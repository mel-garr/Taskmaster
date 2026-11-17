import unittest

from src.config import validate_config


class TestConfig(unittest.TestCase):

    def test_valid_config(self):
        config = {
            "programs": [
                {
                    "name": "worker",
                    "cmd": "python3 worker.py"
                }
            ]
        }

        self.assertTrue(validate_config(config))


if __name__ == "__main__":
    unittest.main()