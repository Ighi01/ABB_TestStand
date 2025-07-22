import subprocess
import os
import sys
import time

TESTEXEC_EXECUTABLE_PATH = r"C:\Program Files\National Instruments\TestStand 2020\UserInterfaces\Simple\VB.Net\Source Code\bin\x64\release\TestExec.exe"
RELATIVE_SEQUENCE_FILE_PATH = os.path.join('..', '..', 'TestRunner.seq')

def run_test_sequence():
    final_return_code = 1

    try:
        try:
            script_directory = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            script_directory = os.getcwd()

        absolute_sequence_file_path = os.path.abspath(os.path.join(script_directory, RELATIVE_SEQUENCE_FILE_PATH))

        if not os.path.exists(TESTEXEC_EXECUTABLE_PATH):
            return 101

        if not os.path.exists(absolute_sequence_file_path):
            return 102

        command_arguments = [
            TESTEXEC_EXECUTABLE_PATH,
            "-Quit",
            "-RunEntryPoint",
            "Single Pass",
            absolute_sequence_file_path
        ]

        try:
            process_result = subprocess.run(
                command_arguments,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False
            )
            final_return_code = process_result.returncode
        except FileNotFoundError:
            final_return_code = 101
        except PermissionError:
            final_return_code = 103
        except Exception:
            final_return_code = -2
        
        return final_return_code

    except Exception:
        return -3

if __name__ == "__main__":
    exit_code = run_test_sequence()
    sys.exit(exit_code)
    


