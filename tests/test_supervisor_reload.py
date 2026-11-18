
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
        self.start_calls = 0
        self.stop_calls = 0

    def start(self):
        self.start_calls += 1
        self.popen = SimpleNamespace(pid=100 + self.start_calls)
        self.alive = True
        self.started_at = 10
        return True

    def stop(self):
        self.stop_calls += 1
        self.alive = False
        return True

    def is_alive(self):
        return self.alive


def make_config(
    name="worker",
    cmd="python worker.py",
    numprocs=1,
    autostart=True,
    autorestart="unexpected",
):
    return SimpleNamespace(
        name=name,
        cmd=cmd,
        numprocs=numprocs,
        autostart=autostart,
        autorestart=autorestart,
        exitcodes=[0],
        starttime=1.0,
        startretries=3,
        stopsignal="TERM",
        stoptime=10.0,
        stdout=None,
        stderr=None,
        env={},
        workingdir=None,
        umask=0o022,
    )


class TestSupervisorReload(unittest.TestCase):

    def setUp(self):
        self.process_patch = patch(
            "src.supervisor.Process",
            FakeProcess,
        )
        self.process_patch.start()
        self.addCleanup(self.process_patch.stop)

    def create_supervisor(self, *configs):
        return Supervisor(list(configs))

    def test_unchanged_program_preserves_process(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")
        original = supervisor.processes["worker"][0]

        self.assertTrue(supervisor.reload([make_config()]))

        self.assertIs(supervisor.processes["worker"][0], original)
        self.assertEqual(original.start_calls, 1)
        self.assertTrue(original.is_alive())

    def test_changed_program_restarts_process(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")
        original = supervisor.processes["worker"][0]

        new_config = make_config(cmd="python new_worker.py")

        self.assertTrue(supervisor.reload([new_config]))

        replacement = supervisor.processes["worker"][0]

        self.assertIsNot(replacement, original)
        self.assertEqual(original.stop_calls, 1)
        self.assertTrue(replacement.is_alive())

    def test_new_program_is_added_and_started(self):
        supervisor = self.create_supervisor(make_config())

        logger_config = make_config(
            name="logger",
            autostart=True,
        )

        self.assertTrue(
            supervisor.reload([make_config(), logger_config])
        )

        self.assertIn("logger", supervisor.processes)
        self.assertTrue(
            supervisor.processes["logger"][0].is_alive()
        )

    def test_removed_program_is_stopped_and_deleted(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")
        original = supervisor.processes["worker"][0]

        self.assertTrue(supervisor.reload([]))

        self.assertNotIn("worker", supervisor.processes)
        self.assertEqual(original.stop_calls, 1)

    def test_increasing_numprocs_preserves_and_starts_processes(self):
        supervisor = self.create_supervisor(make_config())

        supervisor.start_program("worker")
        original = supervisor.processes["worker"][0]

        new_config = make_config(numprocs=3)

        self.assertTrue(supervisor.reload([new_config]))

        processes = supervisor.processes["worker"]

        self.assertEqual(len(processes), 3)
        self.assertIs(processes[0], original)
        self.assertTrue(processes[0].is_alive())
        self.assertTrue(processes[1].is_alive())
        self.assertTrue(processes[2].is_alive())

    def test_decreasing_numprocs_preserves_remaining_processes(self):
        supervisor = self.create_supervisor(make_config(numprocs=3))

        supervisor.start_program("worker")
        original_processes = supervisor.processes["worker"]

        new_config = make_config(numprocs=1)

        self.assertTrue(supervisor.reload([new_config]))

        processes = supervisor.processes["worker"]

        self.assertEqual(len(processes), 1)
        self.assertIs(processes[0], original_processes[0])

        self.assertEqual(original_processes[0].stop_calls, 0)
        self.assertEqual(original_processes[1].stop_calls, 1)
        self.assertEqual(original_processes[2].stop_calls, 1)


if __name__ == "__main__":
    unittest.main()
