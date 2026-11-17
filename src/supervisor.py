import time

from src.process import Process

class Supervisor:
    def __init__(self, configs):
        self.processes = {}
        self.restart_attempts = {}

        for config in configs:
            self.processes[config.name] = [
                Process(config) for _ in range(config.numprocs)
            ]
        
        self.enabled = set()
    
    def start_program(self, name):
        if name not in self.processes:
            return False

        self.enabled.add(name)
        success = True

        for process in self.processes[name]:
            if not process.is_alive():
                if not process.start():
                    success = False
        return  success

    def stop_program(self, name):
        if name not in self.processes:
            return False
        self.enabled.discard(name)
        success = True

        for process in self.processes[name]:
            if not process.stop():
                success = False
        
        return success

    def restart_program(self, name):
        if not self.stop_program(name):
            return False

        return self.start_program(name)
    
    def start_all(self):
        success = True

        for name in self.processes:
            if not self.start_program(name):
                success = False
        return success
    
    def start_autostart(self):
        success = True

        for name, processes in self.processes.items():
            if processes and processes[0].config.autostart:
                if not self.start_program(name):
                    success = False
                
        return success
    def stop_all(self):
        success = True

        for name in list(self.processes):
            if not self.stop_program(name):
                success = False

        return success

    def get_status(self, name):
        if name not in self.processes:
            return None

        return [
            {
                "name": name,
                "pid": process.popen.pid if process.is_alive() else None,
                "status": process.get_status(),
                "exit_code": process.get_exit_code(),
            }
            for process in self.processes[name]
        ]

    def get_all_status(self):
        statuses = {}

        for name in self.processes:
            statuses[name] = self.get_status(name)

        return statuses

    def monitor_once(self):
        for name, processes in self.processes.items():
            if name not in self.enabled:
                continue

            for index, process in enumerate(processes):
                if process.is_alive():
                    continue

                if process.popen is None:
                    continue

                config = process.config
                exit_code = process.get_exit_code()

                should_restart = (
                    config.autorestart == "always"
                    or (
                        config.autorestart == "unexpected"
                        and exit_code not in config.exitcodes
                    )
                )

                if not should_restart:
                    continue

                key = (name, index)
                attempts = self.restart_attempts.get(key, 0)

                if process.started_at is not None:
                    runtime = time.monotonic() - process.started_at

                    if runtime >= config.starttime:
                        attempts = 0

                if attempts >= config.startretries:
                    continue

                self.restart_attempts[key] = attempts + 1
                process.start()

    def run(self, interval=0.5):
        try:
            while True:
                self.monitor_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stop_all()

    def shutdown(self):
        return self.stop_all()
