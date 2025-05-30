import datetime
import os
import sys
import traceback
import logging

from typing import Callable, Dict, Any, List

class FeedbackHandler:
    def __init__(self,
                 initial_code_generator: Callable[[str, Dict[str, str]], str],
                 feedback_code_generator: Callable[[str, str, str, str, Dict[str, str]], str],
                 script_executor: Any,
                 netunicorn_credentials: Dict[str, str],
                 max_retries: int = 3):
        """
        Initializes the FeedbackHandler.

        Args:
            initial_code_generator: Function to generate the first script.
                                    Expected signature: (prompt: str, credentials: dict) -> str
            feedback_code_generator: Function to regenerate script based on feedback.
                                     Expected signature: (original_prompt: str, prev_code: str, stdout: str, stderr: str, credentials: dict) -> str
            script_executor: An instance of the ScriptExecutor class.
            netunicorn_credentials: Dict containing 'endpoint', 'login', 'password'.
            max_retries: Maximum number of retries after the initial attempt.
        """
        self.initial_code_generator = initial_code_generator
        self.feedback_code_generator = feedback_code_generator
        self.script_executor = script_executor
        self.max_retries = max_retries
        self.netunicorn_credentials = netunicorn_credentials
        self.logger = logging.getLogger(f"FeedbackHandler.{id(self)}") 
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def _get_script_filepath(self, base_path: str, user_prompt: str, attempt: int) -> str:
        """Generates a unique script filepath for an attempt."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        sane_prompt = "".join(c if c.isalnum() or c.isspace() else "" for c in user_prompt)
        sane_prompt = sane_prompt.replace(" ", "_")[:30] 
        filename = f"nu_script_attempt_{attempt}_{timestamp}_{sane_prompt}.py"
        
        # Ensure base_path directory exists
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            print(f"Created directory for attempt scripts: {base_path}")
            
        return os.path.join(base_path, filename)

    def _save_script(self, code: str, base_path: str, attempt: int, user_prompt: str, final_name_override: str = None, is_final_successful: bool = False) -> str:
        os.makedirs(base_path, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        sane_prompt_suffix = "".join(c if c.isalnum() or c.isspace() else "" for c in user_prompt)
        sane_prompt_suffix = sane_prompt_suffix.replace(" ", "_")[:30]

        if final_name_override and (is_final_successful or (not is_final_successful and attempt == self.max_retries)):
            filename = final_name_override
            if ".." in filename or os.path.isabs(filename) or filename.startswith(("/", "\\")):
                 self.logger.warning(f"Potentially unsafe final_name_override: '{final_name_override}'. Using default naming convention for safety.")
                 prefix = "nu_script_SUCCESSFUL_" if is_final_successful else f"nu_script_LAST_ATTEMPT_{attempt}_"
                 filename = f"{prefix}{timestamp}_{sane_prompt_suffix}.py"
        else:
            filename = f"nu_script_attempt_{attempt}_{timestamp}_{sane_prompt_suffix}.py"
            
        filepath = os.path.join(base_path, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            self.logger.info(f"Script for attempt {attempt} (final_override: {final_name_override}, is_final_successful: {is_final_successful}) saved to: {filepath}")
        except IOError as e:
            self.logger.error(f"Failed to save script to {filepath}: {e}")
            return None
        return filepath

    def run_generation_with_feedback(self, 
                                     user_prompt: str, 
                                     save_script_base_path: str = None,
                                     final_script_name_override: str = None) -> Dict[str, Any]:
        """
        Manages the code generation, execution, and feedback loop.

        Args:
            user_prompt: The initial user prompt for code generation.
            save_script_base_path: If provided, path to directory where scripts from each attempt are saved. 
                                   Example: "nl4netunicorn_llm/generated_scripts/feedback_attempts"
            final_script_name_override: If save_script_base_path is also provided, this will be the name
                                        of the final successful script (or last attempt if all fail).
                                        If None, a default name based on the last attempt is used.


        Returns:
            A dictionary with:
                - "final_code": str (the last generated script)
                - "report_log": list[dict] (log of all attempts)
                - "success": bool (True if any attempt was successful)
                - "last_execution_output": dict (output from the last execution attempt or successful one)
                - "final_script_path": str (path to the final saved script, if saving was enabled)
        """
        report_log: List[Dict[str, Any]] = []
        current_code = ""
        execution_result = None
        overall_success = False
        final_script_path = None

        # Initial attempt (Attempt 0)
        print(f"FeedbackHandler: Initial code generation for prompt: '{user_prompt}'")
        try:
            current_code = self.initial_code_generator(user_prompt, self.netunicorn_credentials)
        except Exception as e:
            error_msg = f"Error during initial code generation: {e}\n{traceback.format_exc()}"
            print(error_msg, file=sys.stderr)
            report_log.append({
                "attempt": 0,
                "prompt": user_prompt,
                "code_generated": False,
                "error_in_generation": error_msg,
                "execution_result": None
            })
            return {
                "final_code": "",
                "report_log": report_log,
                "success": False,
                "last_execution_output": None,
                "final_script_path": None
            }

        for attempt in range(self.max_retries + 1): # +1 because 0 is initial, then N retries
            print(f"\nFeedbackHandler: Attempt {attempt} (Max retries: {self.max_retries})")
            
            filepath_for_this_attempt = None
            if save_script_base_path:
                filepath_for_this_attempt = self._get_script_filepath(save_script_base_path, user_prompt, attempt)
                print(f"FeedbackHandler: Script for attempt {attempt} will be saved to/run from: {filepath_for_this_attempt}")
            
            attempt_log = {
                "attempt": attempt,
                "code": current_code,
                "filepath_this_attempt": filepath_for_this_attempt,
                "execution_result": None,
                "error_in_generation": None 
            }

            print(f"FeedbackHandler: Executing code for attempt {attempt}...")
            execution_result = self.script_executor.run_script(current_code, script_filepath=filepath_for_this_attempt)
            attempt_log["execution_result"] = execution_result
            print(f"FeedbackHandler: Execution result for attempt {attempt}: Success={execution_result['success']}, ExitCode={execution_result['exit_code']}")
            if execution_result.get("stdout"):
                print("STDOUT:\n" + execution_result["stdout"])
            if execution_result.get("stderr"):
                print("STDERR:\n" + execution_result["stderr"])

            if execution_result["success"]:
                print(f"FeedbackHandler: Attempt {attempt} successful.")
                overall_success = True
                report_log.append(attempt_log)
                final_script_path = filepath_for_this_attempt # This attempt's script is the one that succeeded
                break  # Exit loop on success
            else:
                print(f"FeedbackHandler: Attempt {attempt} failed. Exit code: {execution_result['exit_code']}")
                report_log.append(attempt_log)
                if attempt < self.max_retries:
                    print(f"FeedbackHandler: Requesting code regeneration (Retry {attempt + 1}/{self.max_retries})...")
                    try:
                        current_code = self.feedback_code_generator(
                            user_prompt,
                            current_code,
                            execution_result["stdout"],
                            execution_result["stderr"],
                            self.netunicorn_credentials
                        )
                    except Exception as e:
                        error_msg = f"Error during feedback code generation (attempt {attempt+1}): {e}\n{traceback.format_exc()}"
                        print(error_msg, file=sys.stderr)
                        attempt_log["error_in_regeneration"] = error_msg 
                        break
                else:
                    print(f"FeedbackHandler: Max retries reached ({self.max_retries}).")
        
        if overall_success and save_script_base_path and final_script_name_override and final_script_path:
            overridden_path = os.path.join(save_script_base_path, final_script_name_override)
            try:
                os.makedirs(os.path.dirname(overridden_path), exist_ok=True)
                if os.path.exists(overridden_path):
                    os.remove(overridden_path)
                os.rename(final_script_path, overridden_path)
                print(f"FeedbackHandler: Successful script '{final_script_path}' renamed to '{overridden_path}'")
                final_script_path = overridden_path
            except OSError as e:
                print(f"FeedbackHandler: Error renaming successful script to '{overridden_path}': {e}. Keeping original name: '{final_script_path}'.", file=sys.stderr)
        elif not overall_success and save_script_base_path and final_script_name_override:
            # If all attempts failed, but we have an override name, save the *last* attempted code there.
            last_attempt_code = report_log[-1]["code"] if report_log else ""
            if last_attempt_code:
                overridden_path = os.path.join(save_script_base_path, final_script_name_override)
                try:
                    os.makedirs(os.path.dirname(overridden_path), exist_ok=True)
                    with open(overridden_path, "w", encoding="utf-8") as f:
                        f.write(last_attempt_code)
                    print(f"FeedbackHandler: Last attempted script saved to '{overridden_path}' as all attempts failed.")
                    final_script_path = overridden_path
                except IOError as e:
                    print(f"FeedbackHandler: Error saving last attempted script to '{overridden_path}': {e}.", file=sys.stderr)
                    final_script_path = report_log[-1]["filepath_this_attempt"] if report_log else None # Fallback to last attempt's temp name

        return {
            "final_code": current_code, # This will be the last generated code (successful or last attempt)
            "report_log": report_log,
            "success": overall_success,
            "last_execution_output": execution_result, # Output of the last script that was run
            "final_script_path": final_script_path
        }

    def _rename_final_script(self, current_filepath: str, final_name_override: str, is_successful: bool) -> str | None:
        """Helper to rename a script to its final_name_override and log appropriately."""
        if not current_filepath or not os.path.exists(current_filepath):
            self.logger.error(f"_rename_final_script: Source file {current_filepath} does not exist.")
            return None
        
        target_dir = os.path.dirname(current_filepath)
        new_final_path = os.path.join(target_dir, final_name_override)

        if ".." in final_name_override or os.path.isabs(final_name_override) or final_name_override.startswith(("/", "\\")):
            self.logger.warning(f"Potentially unsafe final_name_override: '{final_name_override}' for renaming. Aborting rename.")
            return current_filepath 
        try:
            if os.path.abspath(current_filepath) == os.path.abspath(new_final_path):
                self.logger.info(f"Script '{current_filepath}' already has the final name. No rename needed.")
                return current_filepath
            
            if os.path.exists(new_final_path):
                self.logger.warning(f"Final script name '{new_final_path}' already exists. Keeping original attempt-named file: '{current_filepath}'")
                return current_filepath 
            
            os.rename(current_filepath, new_final_path)
            status_log = "successful" if is_successful else "last attempted (failed)"
            self.logger.info(f"Script '{current_filepath}' for {status_log} attempt renamed to '{new_final_path}'")
            return new_final_path
        except OSError as e:
            status_log = "successful" if is_successful else "last failed"
            self.logger.error(f"Failed to rename {status_log} script '{current_filepath}' to '{new_final_path}': {e}. Keeping original attempt name.")
            return current_filepath 
if __name__ == '__main__':
    class MockScriptExecutor:
        def run_script(self, script_content: str, script_filepath: str = None):
            print(f"MockExecutor: Running script (path: {script_filepath if script_filepath else 'temp'}). Content:\n{script_content[:100]}...")
            if "error" in script_content.lower():
                return {"success": False, "stdout": "Simulated output", "stderr": "Simulated error", "exit_code": 1, "filepath": script_filepath or "temp.py"}
            if "fail_generation_next" in script_content.lower(): # special keyword to test feedback_code_generator failure
                return {"success": False, "stdout": "Simulated output for gen fail", "stderr": "Simulated error for gen fail", "exit_code": 1, "filepath": script_filepath or "temp.py"}
            return {"success": True, "stdout": "Simulated success!", "stderr": "", "exit_code": 0, "filepath": script_filepath or "temp.py"}

    def mock_initial_generator(prompt, creds):
        print(f"MockInitialGenerator: Prompt='{prompt}', Creds='{creds['login']}'")
        if "initial_error" in prompt:
             raise ValueError("Simulated error in initial generation!")
        return f"# Initial script for {prompt}\nprint('Hello from initial script')"

    def mock_feedback_generator(original_prompt, prev_code, stdout, stderr, creds):
        print(f"MockFeedbackGenerator: Original='{original_prompt}', PrevCode='{prev_code[:30]}...', stdout='{stdout}', stderr='{stderr}', Creds='{creds['login']}'")
        if "fail_generation_next" in prev_code.lower(): # check if the *previous code* hinted at this
            raise ValueError("Simulated error during feedback generation!")
        return f"# Corrected script for {original_prompt}\n# Error was: {stderr}\nprint('Hello from corrected script')"

    mock_executor = MockScriptExecutor()
    mock_creds = {"endpoint": "mock_ep", "login": "mock_user", "password": "mock_pass"}
    
    feedback_handler = FeedbackHandler(
        initial_code_generator=mock_initial_generator,
        feedback_code_generator=mock_feedback_generator,
        script_executor=mock_executor,
        netunicorn_credentials=mock_creds
    )

    print("\n--- Test Case 1: Success on first try ---")
    result1 = feedback_handler.run_generation_with_feedback("test prompt success", save_script_base_path="./generated_feedback_scripts", final_script_name_override="final_successful_script.py")
    print(f"Result 1: Success={result1['success']}\nFinal Code:\n{result1['final_code']}\nReport entries: {len(result1['report_log'])}\nFinal Path: {result1['final_script_path']}")


    print("\n--- Test Case 2: Fails once, then succeeds ---")
    result2 = feedback_handler.run_generation_with_feedback("test prompt error then success", save_script_base_path="./generated_feedback_scripts")
    print(f"Result 2: Success={result2['success']}\nFinal Code:\n{result2['final_code']}\nReport entries: {len(result2['report_log'])}\nFinal Path: {result2['final_script_path']}")


    print("\n--- Test Case 3: All attempts fail ---")
    result3 = feedback_handler.run_generation_with_feedback("test prompt error error error", save_script_base_path="./generated_feedback_scripts", final_script_name_override="last_failed_attempt.py")
    print(f"Result 3: Success={result3['success']}\nFinal Code:\n{result3['final_code']}\nReport entries: {len(result3['report_log'])}\nFinal Path: {result3['final_script_path']}")

    print("\n--- Test Case 4: Initial generation fails ---")
    result4 = feedback_handler.run_generation_with_feedback("test initial_error prompt", save_script_base_path="./generated_feedback_scripts")
    print(f"Result 4: Success={result4['success']}\nFinal Code:\n{result4['final_code']}\nReport entries: {len(result4['report_log'])}\nFinal Path: {result4['final_script_path']}")

    print("\n--- Test Case 5: Feedback generation fails ---")
    def failing_initial_generator(prompt, creds):
        return "# Script that will cause feedback_code_generator to fail_generation_next\nprint('hello')"
    
    feedback_handler_test5 = FeedbackHandler(
        initial_code_generator=failing_initial_generator, 
        feedback_code_generator=mock_feedback_generator,
        script_executor=mock_executor, 
        netunicorn_credentials=mock_creds
    )
    result5 = feedback_handler_test5.run_generation_with_feedback("test feedback_gen_error", save_script_base_path="./generated_feedback_scripts")
    print(f"Result 5: Success={result5['success']}\nFinal Code:\n{result5['final_code']}\nReport entries: {len(result5['report_log'])}")
    if result5['report_log'] and result5['report_log'][-1].get('error_in_regeneration'):
        print(f"Error in regeneration: {result5['report_log'][-1]['error_in_regeneration']}")