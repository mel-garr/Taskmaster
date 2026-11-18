
import unittest
from unittest.mock import Mock, patch

from src.shell import Shell


class TestShell(unittest.TestCase):

    def setUp(self):
        self.supervisor = Mock()
        self.shell = Shell(self.supervisor)

    def test_start_command(self):
        self.supervisor.start_program.return_value = True

        self.shell.execute("start worker")

        self.supervisor.start_program.assert_called_once_with("worker")

    def test_stop_command(self):
        self.supervisor.stop_program.return_value = True

        self.shell.execute("stop worker")

        self.supervisor.stop_program.assert_called_once_with("worker")

    def test_restart_command(self):
        self.supervisor.restart_program.return_value = True

        self.shell.execute("restart worker")

        self.supervisor.restart_program.assert_called_once_with("worker")

    def test_start_missing_argument(self):
        with patch("builtins.print") as mocked_print:
            self.shell.execute("start")

        mocked_print.assert_called()

        self.supervisor.start_program.assert_not_called()

    def test_stop_missing_argument(self):
        with patch("builtins.print") as mocked_print:
            self.shell.execute("stop")

        mocked_print.assert_called()
        self.supervisor.stop_program.assert_not_called()

    def test_restart_missing_argument(self):
        with patch("builtins.print") as mocked_print:
            self.shell.execute("restart")

        mocked_print.assert_called()
        self.supervisor.restart_program.assert_not_called()

    def test_unknown_command(self):
        with patch("builtins.print") as mocked_print:
            result = self.shell.execute("unknown")

        self.assertTrue(result)
        mocked_print.assert_called()

    def test_empty_command(self):
        self.assertTrue(self.shell.execute(""))

    def test_exit_command(self):
        self.assertFalse(self.shell.execute("exit"))

    def test_quit_command(self):
        self.assertFalse(self.shell.execute("quit"))

    def test_help_command(self):
        with patch("builtins.print") as mocked_print:
            self.assertTrue(self.shell.execute("help"))

        mocked_print.assert_called()

    def test_status_command(self):
        self.supervisor.get_all_status.return_value = {}

        with patch("builtins.print"):
            self.shell.execute("status")

        self.supervisor.get_all_status.assert_called_once()

    def test_status_specific_program(self):
        self.supervisor.get_status.return_value = [
            {
                "name": "worker",
                "pid": 1234,
                "status": "running",
                "exit_code": None,
            }
        ]

        with patch("builtins.print"):
            self.shell.execute("status worker")

        self.supervisor.get_status.assert_called_once_with("worker")

    def test_status_unknown_program(self):
        self.supervisor.get_status.return_value = None

        with patch("builtins.print") as mocked_print:
            self.shell.execute("status unknown")

        mocked_print.assert_called()

    def test_start_failed(self):
        self.supervisor.start_program.return_value = False

        with patch("builtins.print") as mocked_print:
            self.shell.execute("start worker")

        mocked_print.assert_called()

    def test_invalid_command_syntax(self):
        with patch("builtins.print") as mocked_print:
            result = self.shell.execute('start "worker')

        self.assertTrue(result)
        mocked_print.assert_called()

    def test_run_exit(self):
        with patch("builtins.input", side_effect=["exit"]):
            with patch("builtins.print"):
                self.shell.run()


if __name__ == "__main__":
    unittest.main()
