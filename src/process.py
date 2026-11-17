import os
import signal
import shlex
import subprocess
import time

from src.models import ProgramConfig

class Process:
    def __init__(self, config: ProgramConfig):
        self.config = config
        self.popen = None
        self.started_at = None
        self.stdout_file = None
        self.stderr_file = None

    def start(self):
        if self.is_alive():
            return False

        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL

        try:
            if self.config.stdout:
                os.makedirs(
                    os.path.dirname(self.config.stdout) or ".",
                    exist_ok=True
                )
                self.stdout_file = open(self.config.stdout, "a")
                stdout = self.stdout_file

            if self.config.stderr:
                os.makedirs(
                    os.path.dirname(self.config.stderr) or ".",
                    exist_ok=True
                )
                self.stderr_file = open(self.config.stderr, "a")
                stderr = self.stderr_file
            
            env = os.environ.copy()
            env.update(self.config.env)

            self.popen = subprocess.Popen(
                shlex.split(self.config.cmd),
                stdout=stdout,
                stderr=stderr,
                cwd=self.config.workingdir,
                env=env,
                preexec_fn=lambda: os.umask(self.config.umask)
            )

            self.started_at = time.monotonic()
            return True
        
        except (OSError, ValueError):
            self._close_logs()
            self.popen = None
            return False

    def is_alive(self):
        if self.popen is None:
            return False

        return self.popen.poll() is None

    def get_status(self):
        if self.popen is None:
            return "stopped"

        if self.is_alive():
            return "running"
        
        return "exited"

    def get_exit_code(self):
        if self.popen is None:
            return None

        return self.popen.poll()
    
    def stop(self):
        if not self.is_alive():
            self._close_logs()
            return True

        try:
            sig = getattr(signal, "SIG" + self.config.stopsignal.upper())
            self.popen.send_signal(sig)
            try:
                self.popen.wait(timeout=self.config.stoptime)
            except subprocess.TimeoutExpired:
                self.popen.kill()
                self.popen.wait()
            
            self._close_logs()
            return True

        except (OSError, ValueError, ProcessLookupError):
            self._close_logs()
            return False
        
    def _close_logs(self):
        if self.stdout_file:
            self.stdout_file.close()
            self.stdout_file = None

        if self.stderr_file:
            self.stderr_file.close()
            self.stderr_file = None