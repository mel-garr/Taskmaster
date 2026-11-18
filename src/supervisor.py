
import logging
import os
import time

from src.process import Process


class Supervisor:
    def __init__(self, configs):
        self.processes = {}
        self.restart_attempts = {}
        self.enabled = set()
        self.logged_exits = {}

        # Configure the Taskmaster event log.
        os.makedirs("logs", exist_ok=True)

        self.logger = logging.getLogger("taskmaster.events")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.FileHandler("logs/taskmaster.log")
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        for config in configs:
            self.processes[config.name] = [
                Process(config) for _ in range(config.numprocs)
            ]

    def reload(self, configs):
        """Apply new configurations while preserving unchanged processes."""
        new_configs = {config.name: config for config in configs}
        success = True

        # 1. Remove programs that no longer exist.
        for name in list(self.processes):
            if name not in new_configs:
                if not self.stop_program(name):
                    success = False

                del self.processes[name]

                self.logger.info(
                    "Removed program '%s' during configuration reload",
                    name,
                )

        # 2. Add new programs or update existing ones.
        for name, config in new_configs.items():

            # Add a new program.
            if name not in self.processes:
                self.processes[name] = [
                    Process(config) for _ in range(config.numprocs)
                ]

                self.logger.info(
                    "Added program '%s' during configuration reload",
                    name,
                )

                if config.autostart:
                    if not self.start_program(name):
                        success = False

                continue

            old_processes = self.processes[name]
            old_config = old_processes[0].config

            was_enabled = name in self.enabled

            # Compare all settings except numprocs.
            old_settings = vars(old_config).copy()
            new_settings = vars(config).copy()

            old_settings.pop("numprocs", None)
            new_settings.pop("numprocs", None)

            settings_unchanged = old_settings == new_settings

            if settings_unchanged:
                current_count = len(old_processes)

                if config.numprocs < current_count:
                    # Stop only processes that are no longer needed.
                    for index in range(config.numprocs, current_count):
                        process = old_processes[index]

                        if not process.stop():
                            success = False

                        self.restart_attempts.pop((name, index), None)
                        self.logged_exits.pop((name, index), None)

                    old_processes = old_processes[:config.numprocs]

                elif config.numprocs > current_count:
                    # Create only the additional processes.
                    new_processes = []

                    for _ in range(config.numprocs - current_count):
                        process = Process(config)
                        old_processes.append(process)
                        new_processes.append(process)

                    # If the program was running, start only the new ones.
                    if was_enabled:
                        for offset, process in enumerate(new_processes):
                            index = current_count + offset
                            self.restart_attempts[(name, index)] = 0

                            if process.start():
                                self.logger.info(
                                    "Started additional process for '%s' "
                                    "(process %s, PID %s)",
                                    name,
                                    index,
                                    process.popen.pid,
                                )
                            else:
                                self.logger.error(
                                    "Failed to start additional process "
                                    "for '%s' (process %s)",
                                    name,
                                    index,
                                )
                                success = False

                # Update the config reference of preserved processes.
                for process in old_processes:
                    process.config = config

                self.processes[name] = old_processes

                self.logger.info(
                    "Preserved unchanged program '%s' during reload",
                    name,
                )

            else:
                # The program's settings changed.
                if not self.stop_program(name):
                    success = False

                self.processes[name] = [
                    Process(config) for _ in range(config.numprocs)
                ]

                self.logger.info(
                    "Updated program '%s' during configuration reload",
                    name,
                )

                if was_enabled or config.autostart:
                    if not self.start_program(name):
                        success = False

        self.logger.info("Configuration reload completed")

        return success

    def start_program(self, name):
        if name not in self.processes:
            return False

        self.enabled.add(name)
        success = True

        for index, process in enumerate(self.processes[name]):
            if not process.is_alive():
                key = (name, index)
                self.restart_attempts[key] = 0

                if process.start():
                    self.logger.info(
                        "Started program '%s' (process %s, PID %s)",
                        name,
                        index,
                        process.popen.pid,
                    )
                else:
                    self.logger.error(
                        "Failed to start program '%s' (process %s)",
                        name,
                        index,
                    )
                    success = False

        return success

    def stop_program(self, name):
        if name not in self.processes:
            return False

        self.enabled.discard(name)
        success = True

        for index, process in enumerate(self.processes[name]):
            was_alive = process.is_alive()
            pid = process.popen.pid if was_alive else None

            if not process.stop():
                self.logger.error(
                    "Failed to stop program '%s' (process %s)",
                    name,
                    index,
                )
                success = False
            elif was_alive:
                self.logger.info(
                    "Stopped program '%s' (process %s, PID %s)",
                    name,
                    index,
                    pid,
                )

            self.restart_attempts.pop((name, index), None)

        return success

    def restart_program(self, name):
        if name not in self.processes:
            return False

        self.logger.info("Manually restarting program '%s'", name)

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

                config = process.config
                key = (name, index)
                attempts = self.restart_attempts.get(key, 0)

                # Case 1: The process failed to launch.
                if process.popen is None:
                    if attempts >= config.startretries:
                        continue

                    self.restart_attempts[key] = attempts + 1
                    process.started_at = None

                    if not process.start():
                        self.logger.error(
                            "Automatic launch attempt failed for '%s' "
                            "(process %s, attempt %s)",
                            name,
                            index,
                            attempts + 1,
                        )

                    continue

                # Case 2: The process started but later exited.
                exit_code = process.get_exit_code()

                if self.logged_exits.get(key) is not process.popen:
                    self.logged_exits[key] = process.popen

                    if exit_code not in config.exitcodes:
                        self.logger.warning(
                            "Program '%s' (process %s, PID %s) "
                            "exited unexpectedly with code %s",
                            name,
                            index,
                            process.popen.pid,
                            exit_code,
                        )
                    else:
                        self.logger.info(
                            "Program '%s' (process %s, PID %s) "
                            "exited with expected code %s",
                            name,
                            index,
                            process.popen.pid,
                            exit_code,
                        )

                should_restart = (
                    config.autorestart == "always"
                    or (
                        config.autorestart == "unexpected"
                        and exit_code not in config.exitcodes
                    )
                )

                if not should_restart:
                    continue

                # Reset retries if the previous run lasted long enough.
                if process.started_at is not None:
                    runtime = process.finished_at - process.started_at

                    if runtime >= config.starttime:
                        attempts = 0

                if attempts >= config.startretries:
                    continue

                self.restart_attempts[key] = attempts + 1
                process.started_at = None

                if process.start():
                    self.logger.info(
                        "Automatically restarted program '%s' "
                        "(process %s, PID %s, attempt %s)",
                        name,
                        index,
                        process.popen.pid,
                        attempts + 1,
                    )
                else:
                    self.logger.error(
                        "Automatic restart failed for '%s' (process %s)",
                        name,
                        index,
                    )

    def run(self, interval=0.5):
        try:
            while True:
                self.monitor_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stop_all()

    def shutdown(self):
        self.logger.info("Taskmaster is shutting down")
        return self.stop_all()
