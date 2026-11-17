
import unittest
import os
import tempfile

from src.models import ProgramConfig
from src.process import Process


class TestProcess(unittest.TestCase):

    def make_config(self, cmd, **kwargs):
        return ProgramConfig(
            name="test",
            cmd=cmd,
            autostart=False,
            autorestart="never",
            **kwargs
        )

    def test_start_process(self):
        process = Process(self.make_config("sleep 10"))

        self.assertTrue(process.start())
        self.assertTrue(process.is_alive())

        process.stop()

    def test_stop_process(self):
        process = Process(self.make_config("sleep 10"))

        process.start()

        self.assertTrue(process.stop())
        self.assertFalse(process.is_alive())

    def test_exit_process(self):
        process = Process(self.make_config("true"))

        self.assertTrue(process.start())
        process.popen.wait()

        self.assertEqual(process.get_exit_code(), 0)
        self.assertEqual(process.get_status(), "exited")

    def test_start_twice(self):
        process = Process(self.make_config("sleep 10"))

        self.assertTrue(process.start())
        self.assertFalse(process.start())

        process.stop()

    def test_stop_without_starting(self):
        process = Process(self.make_config("sleep 10"))

        self.assertTrue(process.stop())
        self.assertTrue(process.stop())
        self.assertTrue(process.stop())

    def test_non_zero_exit_code(self):
        process = Process(self.make_config("false"))

        self.assertTrue(process.start())
        process.popen.wait()

        self.assertEqual(process.get_exit_code(), 1)
        self.assertEqual(process.get_status(), "exited")

    def test_start_invalid_command(self):
        process = Process(
            self.make_config("this_command_does_not_exist_12345")
        )

        self.assertFalse(process.start())
        self.assertFalse(process.is_alive())
        self.assertEqual(process.get_status(), "stopped")

    def test_process_initial_status(self):
        process = Process(self.make_config("sleep 10"))

        self.assertFalse(process.is_alive())
        self.assertEqual(process.get_status(), "stopped")
        self.assertIsNone(process.get_exit_code())

    def test_stdout_logging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "stdout.log")

            process = Process(
                self.make_config(
                    "echo hello",
                    stdout=log_path
                )
            )

            self.assertTrue(process.start())
            process.popen.wait()

            with open(log_path, "r") as file:
                output = file.read()

            self.assertEqual(output, "hello\n")
            process.stop()

    def test_stderr_logging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "stderr.log")

            process = Process(
                self.make_config(
                    "sh -c 'echo error >&2'",
                    stderr=log_path
                )
            )

            self.assertTrue(process.start())
            process.popen.wait()

            with open(log_path, "r") as file:
                output = file.read()

            self.assertEqual(output, "error\n")
            process.stop()

    def test_stop_timeout(self):
        process = Process(
            self.make_config(
                "sh -c 'trap \"\" TERM; sleep 30'",
                stoptime=0.5
            )
        )

        self.assertTrue(process.start())

        self.assertTrue(process.stop())
        self.assertFalse(process.is_alive())


if __name__ == "__main__":
    unittest.main()
