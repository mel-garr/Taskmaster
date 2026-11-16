

from dataclasses import dataclass

@dataclass
class ProgramConfig:
    name: str
    cmd: str
    numprocs: int
    autostart: bool
    autorestart: str

