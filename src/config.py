import tomllib

def load_config(path: str) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {path}")
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Error parsing configuration file: {e}") from e
    except PermissionError:
        raise PermissionError(f"Permission denied when accessing configuration file: {path}") from e
