import subprocess
import os
import sys
import platform

def clear_console():
    command = 'cls' if platform.system() == 'Windows' else 'clear'
    os.system(command)

def print_welcome_message():
    print("=============================================")
    print("===   Python Script Runner Console        ===")
    print("=============================================")
    print("\nWelcome! This tool helps you run Python scripts quickly.")
    print("\nCOMMANDS:")
    print("  <filename>.py    - Runs the specified Python script.")
    print("  restart / rerun  - Runs the last executed script again.")
    print("  clear / cls      - Clears the console screen.")
    print("  help             - Shows this welcome message again.")
    print("  exit / quit      - Exits the application.")
    print("-" * 45)

def execute_script(script_path):
    if not os.path.exists(script_path):
        print(f"Error: The file '{script_path}' was not found.")
        return

    print(f"\n--- Running '{os.path.basename(script_path)}' ---\n")
    try:
        python_executable = sys.executable
        result = subprocess.run(
            [python_executable, script_path],
            capture_output=True,
            text=True,
            check=False
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print("--- Errors ---", file=sys.stderr)
            print(result.stderr, end="", file=sys.stderr)
            print("--------------", file=sys.stderr)
        if result.returncode == 0:
            print(f"\n--- Script '{os.path.basename(script_path)}' finished successfully ---")
        else:
            print(f"\n--- Script '{os.path.basename(script_path)}' exited with error code: {result.returncode} ---", file=sys.stderr)
    except FileNotFoundError:
        print(f"Error: The Python interpreter '{sys.executable}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred while trying to run the script: {e}")

def main():
    last_script_path = None
    clear_console()
    print_welcome_message()
    while True:
        try:
            command = input("\n>>> ").strip()
            if not command:
                continue
            if command.lower() in ['exit', 'quit']:
                print("Exiting runner. Goodbye!")
                break
            if command.lower() == 'help':
                print_welcome_message()
                continue
            if command.lower() in ['clear', 'cls']:
                clear_console()
                continue
            if command.lower() in ['restart', 'rerun']:
                if last_script_path:
                    execute_script(last_script_path)
                else:
                    print("No script has been run yet. Please run a script first.")
                continue
            if command.lower().endswith('.py'):
                last_script_path = command
                execute_script(last_script_path)
            else:
                print(f"Unknown command: '{command}'. Please provide a '.py' file or a valid command.")
        except KeyboardInterrupt:
            print("\n\nExiting runner. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn application error occurred: {e}")

if __name__ == "__main__":
    main()
