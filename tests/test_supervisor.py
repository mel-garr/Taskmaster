
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.supervisor import Supervisor


class FakeProcess:
    def __init__(self, config):
        self.config = config
        self.popen = None
        self.started_at = None
        self.finished_at = None
        self.alive = False
        self.exit_code = None

        self.start_calls = 0
        self.stop_calls = 0

        self.start_result = True
        self.stop_result = True

    def start(self):
        self.start_calls += 1

        if not self.start_result:
            self.popen = None
            self.started_at = None
            self.finished_at = None
            self.alive = False
            return False

        self.popen = SimpleNamespace(pid=100 + self.start_calls)
        self.started_at = 10
        self.finished_at = None
        self.alive = True
        self.exit_code = None

        return True

    def stop(self):
        self.stop_calls += 1

        if self.alive:
            self.finished_at = self.started_at + 1

        self.alive = False
        return self.stop_result

    def is_alive(self):
        if not self.alive and self.popen is not None:
            if self.finished_at is None and self.started_at is not None:
                self.finished_at = self.started_at + 1

        return self.alive

    def get_status(self):
        if self.alive:
            return "running"

        if self.popen is None:
            return "stopped"

        return "exited"

    def get_exit_code(self):
        return self.exit_code


def make_config(
    name="worker",
    numprocs=1,
    autostart=True,
    autorestart="unexpected",
    exitcodes=None,
    starttime=1000,
    startretries=3,
):
    return SimpleNamespace(
        name=name,
        numprocs=numprocs,
        autostart=autostart,
        autorestart=autorestart,
        exitcodes=exitcodes if exitcodes is not None else [0],
        starttime=starttime,
        startretries=startretries,
    )


class TestSupervisor(unittest.TestCase):

    def create_supervisor(self, *configs):
        with patch("src.supervisor.Process", FakeProcess):
            supervisor = Supervisor(list(configs))

        return supervisor

    def test_start_program(self):
        supervisor = self.create_supervisor(make_config())

        self.assertTrue(supervisor.start_program("worker"))
        self.assertTrue(supervisor.processes["worker"][0].is_alive())

    def test_start_invalid_program(self):
        supervisor = self.create_supervisor(make_config())

        self.assertFalse(supervisor.start_program("unknown"))

    def test_start_multiple_processes(self):
        supervisor = self.create_supervisor(
            make_config(numprocs=3)
        )

        self.assertTrue(supervisor.start_program("worker"))

        for process in supervisor.processes["worker"]:
            self.assertTrue(process.is_alive())

    def test_stop_program(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")

        self.assertTrue(supervisor.stop_program("worker"))
        self.assertNotIn("worker", supervisor.enabled)

        self.assertFalse(
            supervisor.processes["worker"][0].is_alive()
        )

    def test_restart_program(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")

        self.assertTrue(supervisor.restart_program("worker"))

        process = supervisor.processes["worker"][0]

        self.assertEqual(process.start_calls, 2)
        self.assertEqual(process.stop_calls, 1)
        self.assertTrue(process.is_alive())

    def test_start_all(self):
        supervisor = self.create_supervisor(
            make_config("worker"),
            make_config("logger"),
        )

        self.assertTrue(supervisor.start_all())

        self.assertTrue(supervisor.processes["worker"][0].is_alive())
        self.assertTrue(supervisor.processes["logger"][0].is_alive())

    def test_start_autostart(self):
        supervisor = self.create_supervisor(
            make_config("worker", autostart=True),
            make_config("logger", autostart=False),
        )

        self.assertTrue(supervisor.start_autostart())

        self.assertTrue(supervisor.processes["worker"][0].is_alive())
        self.assertFalse(supervisor.processes["logger"][0].is_alive())

    def test_stop_all(self):
        supervisor = self.create_supervisor(
            make_config("worker"),
            make_config("logger"),
        )

        supervisor.start_all()

        self.assertTrue(supervisor.stop_all())

        for processes in supervisor.processes.values():
            for process in processes:
                self.assertFalse(process.is_alive())

    def test_get_status(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")

        status = supervisor.get_status("worker")

        self.assertEqual(len(status), 1)
        self.assertEqual(status[0]["name"], "worker")
        self.assertEqual(status[0]["status"], "running")
        self.assertIsNotNone(status[0]["pid"])

    def test_get_invalid_status(self):
        supervisor = self.create_supervisor(make_config())

        self.assertIsNone(supervisor.get_status("unknown"))

    def test_get_all_status(self):
        supervisor = self.create_supervisor(
            make_config("worker"),
            make_config("logger"),
        )

        statuses = supervisor.get_all_status()

        self.assertIn("worker", statuses)
        self.assertIn("logger", statuses)

    def test_monitor_restart_always(self):
        supervisor = self.create_supervisor(
            make_config(autorestart="always")
        )

        supervisor.start_program("worker")
        process = supervisor.processes["worker"][0]

        process.alive = False
        process.exit_code = 0

        supervisor.monitor_once()

        self.assertEqual(process.start_calls, 2)
        self.assertTrue(process.is_alive())

    def test_monitor_restart_unexpected(self):
        supervisor = self.create_supervisor(
            make_config(autorestart="unexpected", exitcodes=[0])
        )

        supervisor.start_program("worker")
        process = supervisor.processes["worker"][0]

        process.alive = False
        process.exit_code = 1

        supervisor.monitor_once()

        self.assertEqual(process.start_calls, 2)

    def test_monitor_no_restart_on_expected_exit(self):
        supervisor = self.create_supervisor(
            make_config(autorestart="unexpected", exitcodes=[0])
        )

        supervisor.start_program("worker")
        process = supervisor.processes["worker"][0]

        process.alive = False
        process.exit_code = 0

        supervisor.monitor_once()

        self.assertEqual(process.start_calls, 1)

    def test_monitor_retry_failed_start(self):
        supervisor = self.create_supervisor(make_config())

        process = supervisor.processes["worker"][0]
        process.start_result = False

        self.assertFalse(supervisor.start_program("worker"))

        process.start_result = True

        supervisor.monitor_once()

        self.assertEqual(process.start_calls, 2)
        self.assertTrue(process.is_alive())

    def test_monitor_respects_startretries(self):
        supervisor = self.create_supervisor(
            make_config(startretries=2)
        )

        process = supervisor.processes["worker"][0]
        process.start_result = False

        supervisor.start_program("worker")

        supervisor.monitor_once()
        supervisor.monitor_once()
        supervisor.monitor_once()

        # One initial attempt + two retries.
        self.assertEqual(process.start_calls, 3)

    def test_shutdown(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")

        self.assertTrue(supervisor.shutdown())

        self.assertFalse(
            supervisor.processes["worker"][0].is_alive()
        )

    def test_monitor_stops_after_max_retries(self):
        supervisor = self.create_supervisor(
            make_config(
                autorestart="always",
                startretries=2,
            )
        )

        supervisor.start_program("worker")
        process = supervisor.processes["worker"][0]

        # Simulate the first crash.
        process.alive = False
        process.exit_code = 1
        supervisor.monitor_once()

        self.assertEqual(process.start_calls, 2)

        # Simulate the second crash.
        process.alive = False
        process.exit_code = 1
        supervisor.monitor_once()

        self.assertEqual(process.start_calls, 3)

        # Simulate the third crash.
        process.alive = False
        process.exit_code = 1
        supervisor.monitor_once()

        # No third retry should happen.
        self.assertEqual(process.start_calls, 3)

if __name__ == "__main__":
    unittest.main()
