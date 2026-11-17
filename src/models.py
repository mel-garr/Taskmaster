
from dataclasses import dataclass, field


@dataclass
class ProgramConfig:
    name: str
    cmd: str
    numprocs: int = 1
    autostart: bool = True
    autorestart: str = "unexpected"
    exitcodes: list[int] = field(default_factory=lambda: [0])
    starttime: float = 1.0
    startretries: int = 3
    stopsignal: str = "TERM"
    stoptime: float = 10.0
    stdout: str | None = None
    stderr: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    workingdir: str | None = None
    umask: int = 0o022

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "ProgramConfig":
        return cls(
            name=name,
            cmd=data["cmd"],
            numprocs=data.get("numprocs", 1),
            autostart=data.get("autostart", True),
            autorestart=data.get("autorestart", "unexpected"),
            exitcodes=data.get("exitcodes", [0]),
            starttime=data.get("starttime", 1.0),
            startretries=data.get("startretries", 3),
            stopsignal=data.get("stopsignal", "TERM"),
            stoptime=data.get("stoptime", 10.0),
            stdout=data.get("stdout"),
            stderr=data.get("stderr"),
            env=data.get("env", {}),
            workingdir=data.get("workingdir"),
            umask=data.get("umask", 0o022),
        )
