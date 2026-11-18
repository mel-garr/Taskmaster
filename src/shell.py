
import shlex


class Shell:
    def __init__(self, supervisor, reload_callback=None):
        self.supervisor = supervisor
        self.reload_callback = reload_callback

    def execute(self, command):
        try:
            args = shlex.split(command)
        except ValueError:
            print("Error: invalid command syntax")
            return True

        if not args:
            return True

        action = args[0]

        if action == "help":
            self.help()

        elif action == "status":
            self.status(args)

        elif action == "start":
            self.start(args)

        elif action == "stop":
            self.stop(args)

        elif action == "restart":
            self.restart(args)

        elif action == "reload":
            self.reload(args)

        elif action in ("exit", "quit"):
            return False

        else:
            print(f"Unknown command: {action}")
            print("Type 'help' to see available commands.")

        return True

    def help(self):
        print("""
Available commands:
    start <name>     Start a program
    stop <name>      Stop a program
    restart <name>   Restart a program
    status           Show all program statuses
    status <name>    Show one program status
    reload           Reload configuration
    help             Show available commands
    exit             Exit Taskmaster
""")

    def start(self, args):
        if len(args) != 2:
            print("Usage: start <name>")
            return

        name = args[1]

        if self.supervisor.start_program(name):
            print(f"Program '{name}' started successfully.")
        else:
            print(f"Failed to start program '{name}'.")

    def stop(self, args):
        if len(args) != 2:
            print("Usage: stop <name>")
            return

        name = args[1]

        if self.supervisor.stop_program(name):
            print(f"Program '{name}' stopped successfully.")
        else:
            print(f"Failed to stop program '{name}'.")

    def restart(self, args):
        if len(args) != 2:
            print("Usage: restart <name>")
            return

        name = args[1]

        if self.supervisor.restart_program(name):
            print(f"Program '{name}' restarted successfully.")
        else:
            print(f"Failed to restart program '{name}'.")

    def reload(self, args):
        if len(args) != 1:
            print("Usage: reload")
            return

        if self.reload_callback is None:
            print("Configuration reload is not available.")
            return

        if self.reload_callback():
            print("Configuration reloaded successfully.")
        else:
            print("Configuration reload failed.")

    def status(self, args):
        if len(args) > 2:
            print("Usage: status [name]")
            return

        if len(args) == 2:
            name = args[1]
            statuses = self.supervisor.get_status(name)

            if statuses is None:
                print(f"Unknown program: {name}")
                return

            self.display_status(name, statuses)
            return

        all_statuses = self.supervisor.get_all_status()

        if not all_statuses:
            print("No programs configured.")
            return

        for name, statuses in all_statuses.items():
            self.display_status(name, statuses)

    def display_status(self, name, statuses):
        print(f"\nProgram: {name}")

        for index, process in enumerate(statuses):
            pid = process["pid"]
            exit_code = process["exit_code"]

            print(
                f"  Process {index + 1}: "
                f"{process['status']} | "
                f"PID: {pid if pid is not None else '-'} | "
                f"Exit code: {exit_code if exit_code is not None else '-'}"
            )

    def run(self):
        print("Taskmaster started. Type 'help' for commands.")

        while True:
            try:
                command = input("taskmaster> ")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting Taskmaster.")
                break

            if not self.execute(command):
                print("Exiting Taskmaster.")
                break
