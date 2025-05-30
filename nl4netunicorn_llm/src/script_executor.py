import subprocess
import tempfile
import os
import sys # Import sys

class ScriptExecutor:
    def run_script(self, script_content: str, script_filepath: str = None) -> dict:
        """
        Runs the given Python script content in a separate process.

        Args:
            script_content: The Python script code as a string.
            script_filepath: Optional. If provided, the script is saved here before execution. 
                             Otherwise, a temporary file is used.

        Returns:
            A dictionary with:
                - "success": bool (True if exit code is 0, False otherwise)
                - "stdout": str (captured standard output)
                - "stderr": str (captured standard error)
                - "filepath": str (path to the script that was executed)
                - "exit_code": int (the exit code of the script)
        """
        temp_file_created = False
        if script_filepath:
            script_dir = os.path.dirname(script_filepath)
            if script_dir:
                os.makedirs(script_dir, exist_ok=True)
            current_file_path = script_filepath
        else:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py", encoding="utf-8") as tmp_file:
                current_file_path = tmp_file.name
            temp_file_created = True

        try:
            with open(current_file_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            python_executable = sys.executable
            if not python_executable: 
                python_executable = "python"


            process = subprocess.run(
                [python_executable, current_file_path],
                capture_output=True,
                text=True,
                check=False 
            )
            
            success = process.returncode == 0
            return {
                "success": success,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "filepath": current_file_path,
                "exit_code": process.returncode
            }
        finally:
            if temp_file_created and os.path.exists(current_file_path):
                try:
                    os.remove(current_file_path)
                except OSError as e:
                    print(f"Warning: Could not delete temporary script file {current_file_path}: {e}", file=sys.stderr)
            elif not temp_file_created and script_filepath:
                pass 