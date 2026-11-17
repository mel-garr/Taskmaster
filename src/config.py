
import tomllib
import signal

from src.models import ProgramConfig


def load_config(path: str) -> dict:
    try:
        with open(path, "rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {path}")
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Invalid TOML configuration: {error}") from error


def validate_config(config: dict) -> bool:
    if not isinstance(config, dict):
        return False

    programs = config.get("programs")

    if not isinstance(programs, list) or not programs:
        return False

    for program in programs:
        if not isinstance(program, dict):
            return False

        required = ("name", "cmd")

        if any(key not in program for key in required):
            return False

        if not isinstance(program["name"], str) or not program["name"]:
            return False

        if not isinstance(program["cmd"], str) or not program["cmd"]:
            return False

        if not isinstance(program.get("numprocs", 1), int) or isinstance(program.get("numprocs", 1), bool) or program.get("numprocs", 1) < 1:
            return False

        if not isinstance(program.get("autostart", True), bool):
            return False

        if program.get("autorestart", "unexpected") not in ("always", "never", "unexpected"):
            return False

        exitcodes = program.get("exitcodes", [0])

        if not isinstance(exitcodes, list):
            return False

        if any(not isinstance(code, int) or isinstance(code, bool) or not 0 <= code <= 255 for code in exitcodes):
            return False

        if not isinstance(program.get("starttime", 1.0), (int, float)) or isinstance(program.get("starttime", 1.0), bool) or program.get("starttime", 1.0) < 0:
            return False

        if not isinstance(program.get("startretries", 3), int) or isinstance(program.get("startretries", 3), bool) or program.get("startretries", 3) < 0:
            return False

        if not isinstance(program.get("stoptime", 10.0), (int, float)) or isinstance(program.get("stoptime", 10.0), bool) or program.get("stoptime", 10.0) < 0:
            return False

        stopsignal = program.get("stopsignal", "TERM")

        if not isinstance(stopsignal, str) or not hasattr(signal, "SIG" + stopsignal.upper()):
            return False

        for key in ("stdout", "stderr", "workingdir"):
            if program.get(key) is not None and not isinstance(program[key], str):
                return False

        env = program.get("env", {})

        if not isinstance(env, dict):
            return False

        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in env.items()):
            return False

        umask = program.get("umask", 0o022)

        if not isinstance(umask, int) or isinstance(umask, bool) or not 0 <= umask <= 0o777:
            return False

    names = [program["name"] for program in programs]

    return len(names) == len(set(names))


def create_program_configs(config: dict) -> list[ProgramConfig]:
    if not validate_config(config):
        raise ValueError("Invalid configuration")

    return [
        ProgramConfig.from_dict(program["name"], program)
        for program in config["programs"]
    ]
