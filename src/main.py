
import argparse
import signal
import threading

from src.config import load_config, create_program_configs
from src.supervisor import Supervisor
from src.shell import Shell


def monitor_supervisor(
    supervisor,
    stop_event,
    reload_event,
    reload_callback,
    supervisor_lock,
    interval=0.5,
):
    while not stop_event.is_set():

        # Check whether SIGHUP requested a configuration reload.
        if reload_event.is_set():
            reload_event.clear()

            if reload_callback():
                print("Configuration reloaded successfully.")
            else:
                print("Configuration reload failed.")

        # Monitor processes safely.
        with supervisor_lock:
            supervisor.monitor_once()

        stop_event.wait(interval)


def main():
    parser = argparse.ArgumentParser(
        description="Taskmaster process manager"
    )

    parser.add_argument(
        "-c",
        "--config",
        default="config/taskmaster.toml",
        help="Path to the TOML configuration file",
    )

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        configs = create_program_configs(config)
        supervisor = Supervisor(configs)

    except (OSError, ValueError) as error:
        print(f"Configuration error: {error}")
        return 1

    if not supervisor.start_autostart():
        print("Warning: one or more programs failed to start.")

    # Synchronize reloads and monitoring.
    supervisor_lock = threading.RLock()

    def reload_config():
        try:
            # Load and validate before changing running programs.
            config = load_config(args.config)
            configs = create_program_configs(config)

            with supervisor_lock:
                return supervisor.reload(configs)

        except (OSError, ValueError) as error:
            print(f"Configuration reload error: {error}")
            return False

    # Event used to request a reload from SIGHUP.
    reload_event = threading.Event()

    def handle_sighup(signum, frame):
        # Keep the signal handler simple and safe.
        reload_event.set()

    signal.signal(signal.SIGHUP, handle_sighup)

    stop_event = threading.Event()

    monitor_thread = threading.Thread(
        target=monitor_supervisor,
        args=(
            supervisor,
            stop_event,
            reload_event,
            reload_config,
            supervisor_lock,
        ),
        daemon=True,
    )

    monitor_thread.start()

    shell = Shell(supervisor, reload_callback=reload_config)

    try:
        shell.run()

    finally:
        stop_event.set()
        monitor_thread.join()

        with supervisor_lock:
            supervisor.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
