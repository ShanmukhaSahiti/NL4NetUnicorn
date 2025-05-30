# nl4netunicorn_llm/examples/generate_netunicorn_script.py
import sys
import os
import logging # For seeing logs from RAG system

# Ensure the nl4netunicorn_llm module can be found
# This adjusts the Python path to include the project root if the script is run from the examples directory.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir)) # Assuming examples is one level down from src, and src is one level from project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from nl4netunicorn_llm.src.netunicorn_rag import NetUnicornRAG

# Setup basic logging for the example script itself to see RAG logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_results(result_dict):
    logger.info(f"Overall Success: {result_dict.get('success')}")
    logger.info(f"Final Generated Code:\n{result_dict.get('final_code')}")
    final_script_path = result_dict.get('final_script_path')
    if final_script_path:
        logger.info(f"Final script saved to: {final_script_path}")
    else:
        logger.info("Final script was not saved (or an error occurred during saving/cleanup).")
    
    logger.info("Execution Report Log:")
    for entry in result_dict.get("report_log", []):
        logger.info(f"  Attempt {entry.get('attempt')}:")
        logger.info(f"    Code Generated: {'Yes' if entry.get('code') else ('No - Error: ' + entry.get('error_in_generation', 'Unknown generation error') if entry.get('error_in_generation') else 'No - Error: ' + entry.get('error_in_regeneration', 'Unknown regeneration error'))}")
        if entry.get('filepath_this_attempt'): 
            logger.info(f"    Filepath for attempt: {entry.get('filepath_this_attempt')}")
        exec_res = entry.get('execution_result')
        if exec_res:
            logger.info(f"    Execution Success: {exec_res.get('success')}, Exit Code: {exec_res.get('exit_code')}")
            stdout = exec_res.get('stdout', '').strip()
            stderr = exec_res.get('stderr', '').strip()
            if stdout:
                logger.info(f"    STDOUT: {stdout[:200]}{'...' if len(stdout) > 200 else ''}")
            if stderr:
                logger.info(f"    STDERR: {stderr[:200]}{'...' if len(stderr) > 200 else ''}")
        elif not entry.get('error_in_generation') and not entry.get('error_in_regeneration'):
            logger.info("    Execution Result: Not available (Code may not have been run due to prior error or configuration)")
    logger.info("-------------------------------------------")

def main():
    try:
        logger.info("Initializing NetUnicornRAG system...")
        rag_system = NetUnicornRAG()
        
        # Test Case 1: Feedback loop with default retries (3)
        logger.info("\n--- Example 1: Generating with Feedback Loop (default max_retries=3) ---")
        prompt1 = "Create a NetUnicorn script that connects to the server, selects one available node, and runs a sleep task for 10 seconds. Ensure all results are printed."
        logger.info(f"Sending prompt to RAG system: \"{prompt1}\"")
        results1 = rag_system.generate_code(
            user_prompt=prompt1,
            save_final_script=True,
            enable_feedback_loop=True # This is the default for generate_code, but explicit for clarity
            # max_retries will use the default of 3 from NetUnicornRAG
        )
        print_results(results1)

        # Test Case 2: Simulating "generate and run once" by setting max_retries=0
        logger.info("\n--- Example 2: Simulating Generate and Run Once (max_retries=0) ---")
        prompt2 = "Create a NetUnicorn script that tries to import a non_existent_module and then runs a sleep task for 5 seconds."
        logger.info(f"Sending prompt to RAG system: \"{prompt2}\"")
        results2 = rag_system.generate_code(
            user_prompt=prompt2,
            save_final_script=True,
            enable_feedback_loop=True, 
            max_retries=0 
        )
        print_results(results2)

        # Test Case 3: Generation only (no execution, no feedback beyond initial generation)
        logger.info("\n--- Example 3: Generation Only (No Execution, No Retries) ---")
        prompt3 = "Generate a NetUnicorn pipeline with a single SleepTask(10), ensuring all imports like RemoteClient, Pipeline, and SleepTask are present."
        logger.info(f"Sending prompt to RAG system: \"{prompt3}\"")
        results3 = rag_system.generate_code(
            user_prompt=prompt3,
            save_final_script=False, 
            enable_feedback_loop=False 
        )
        print_results(results3)
        if results3.get('final_script_path') is not None:
            logger.error(f"Test Case 3 Error: Final script path was {results3.get('final_script_path')} but should be None when save_final_script is False.")
        
        # Test Case 4: Prompt for ShellCommand (expect success now)
        logger.info("\n--- Example 4: Prompt for ShellCommand (expect success) ---")
        prompt4 = "Create a NetUnicorn script that runs a shell command 'echo Hello from ShellCommand'. Use ShellCommand from basic tasks."
        logger.info(f"Sending prompt to RAG system: \"{prompt4}\"")
        results4 = rag_system.generate_code(
            user_prompt=prompt4,
            save_final_script=True,
            enable_feedback_loop=True,
            max_retries=2 
        )
        print_results(results4)

        logger.info("\n--- Example Script Finished ---")

    except FileNotFoundError as e:
        logger.error(f"ERROR: A required file was not found. {e}. Please ensure your .env file (in project root) and documentation JSON (e.g., nl4netunicorn_llm/data/netunicorn_docs.json) exist and paths are correct.")
        import traceback
        traceback.print_exc()
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 