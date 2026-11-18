# Taskmaster

Taskmaster is a process manager written in Python. It manages child processes, monitors their execution, automatically restarts them according to configurable policies, and provides an interactive shell for process control.

## Features

- Start and stop child processes.
- Manage multiple instances of a program.
- Monitor processes and detect unexpected exits.
- Automatically restart processes according to configurable policies.
- Configure startup retries and timing.
- Redirect standard output and standard error to log files.
- Configure environment variables, working directories, and file permissions.
- Reload configuration without shutting down Taskmaster.
- Preserve unchanged processes during configuration reloads.
- Handle `SIGHUP` to trigger configuration reloads.
- Record process events in a local log file.
- Interactive shell for managing programs.

## Requirements

- Python 3.11 or newer.
- Linux or another compatible Unix-like operating system.
- `make` (optional, for using the Makefile).

Taskmaster uses Python's standard library. No additional Python packages are required.

## Project Structure

```text
taskmaster/
├── config/
│   └── taskmaster.toml
├── examples/
│   └── worker.py
├── logs/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── models.py
│   ├── process.py
│   ├── shell.py
│   └── supervisor.py
├── tests/
├── Makefile
└── README.md
```

## Running Taskmaster

Clone or navigate to the project directory:

```bash
cd taskmaster
```

Start Taskmaster with the default configuration:

```bash
python3 -m src.main
```

Alternatively, use Make:

```bash
make run
```

To specify a different configuration file:

```bash
python3 -m src.main -c path/to/config.toml
```

Taskmaster starts configured programs with `autostart = true` and opens its interactive shell.

## Configuration

Taskmaster uses TOML configuration files.

Example configuration:

```toml
[[programs]]
name = "worker"
cmd = "python3 examples/worker.py"
numprocs = 1
autostart = true
autorestart = "unexpected"
exitcodes = [0]
starttime = 1
startretries = 3
stopsignal = "TERM"
stoptime = 10
stdout = "logs/worker.log"
stderr = "logs/worker_error.log"
workingdir = "."
umask = 18

[programs.env]
TASKMASTER = "true"
```

### Configuration Options

| Option | Description | Default |
|---|---|---|
| `name` | Program identifier | Required |
| `cmd` | Command used to launch the program | Required |
| `numprocs` | Number of process instances | `1` |
| `autostart` | Start the program when Taskmaster launches | `true` |
| `autorestart` | Restart policy: `always`, `never`, or `unexpected` | `unexpected` |
| `exitcodes` | Exit codes considered successful | `[0]` |
| `starttime` | Runtime required to consider a startup successful | `1.0` |
| `startretries` | Maximum automatic startup/restart attempts | `3` |
| `stopsignal` | Signal sent when stopping a process | `TERM` |
| `stoptime` | Time to wait before forcefully killing a process | `10.0` |
| `stdout` | File used for standard output | `None` |
| `stderr` | File used for standard error | `None` |
| `workingdir` | Working directory for the child process | `None` |
| `env` | Additional environment variables | `{}` |
| `umask` | File creation permission mask | `0o022` |

### Automatic Restart Policies

- `always`: Restart the process whenever it exits.
- `never`: Do not automatically restart the process.
- `unexpected`: Restart only when the exit code is not listed in `exitcodes`.

## Interactive Shell

Once Taskmaster is running, the following commands are available:

| Command | Description |
|---|---|
| `help` | Display available commands |
| `status` | Display the status of all programs |
| `status <name>` | Display the status of a specific program |
| `start <name>` | Start a program |
| `stop <name>` | Stop a program |
| `restart <name>` | Restart a program |
| `reload` | Reload the configuration |
| `exit` | Exit Taskmaster |
| `quit` | Exit Taskmaster |

Example:

```text
taskmaster> status
taskmaster> restart worker
taskmaster> stop worker
taskmaster> start worker
taskmaster> reload
taskmaster> exit
```

## Configuration Reload

Taskmaster supports configuration reloads without shutting down the main process.

You can reload the configuration from the interactive shell:

```text
taskmaster> reload
```

You can also send `SIGHUP` to the Taskmaster process from another terminal:

```bash
kill -HUP <TASKMASTER_PID>
```

On reload, Taskmaster applies configuration changes, adds new programs, removes deleted programs, and restarts programs whose settings have changed.

Unchanged processes are preserved, including when the number of process instances changes.

## Logging

Taskmaster records management events in:

```text
logs/taskmaster.log
```

Events include:

- Process starts and stops.
- Failed process launches.
- Unexpected process exits.
- Automatic restarts.
- Configuration reloads.
- Program additions, removals, and updates.
- Taskmaster shutdown.

Child process output can be redirected to the files configured by `stdout` and `stderr`.

## Running Tests

Run the complete test suite with:

```bash
make test
```

Alternatively:

```bash
python3 -m unittest discover -s tests -v
```

The test suite covers configuration validation, process management, shell commands, supervisor behavior, automatic restarts, and configuration reloads.

## Makefile Commands

| Command | Description |
|---|---|
| `make` | Run Taskmaster |
| `make run` | Start Taskmaster |
| `make test` | Run all unit tests |
| `make clean` | Remove Python cache files |

## Shutdown

Use the `exit` or `quit` command in the interactive shell, or press `Ctrl+C` / send EOF to exit. Taskmaster stops its supervised processes during shutdown.

