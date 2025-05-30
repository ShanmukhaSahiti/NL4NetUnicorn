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

# Example usage (if kept as a library, otherwise this comment is moot)
# if __name__ == "__main__":
#     main() # Or however it's intended to be run. 