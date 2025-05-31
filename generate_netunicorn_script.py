# # nl4netunicorn_llm/examples/generate_netunicorn_script.py
# import sys
# import os
# import argparse

# from netunicorn_rag import NetUnicornRAG

# def main():
#     try:
#         # Parse arguments
#         parser = argparse.ArgumentParser(description='Generate netUnicorn Script')
#         parser.add_argument('-p', '--prompt', dest='prompt', help='Prompt', type=str, required=True)
#         parser.add_argument('-s', '--save_script', dest='save_script', help='Save the generated script in a file', action='store_true')
#         parser.add_argument('-e', '--execute_script', dest='execute_script', help='Execute the generated script', action='store_true')

#         args = parser.parse_args()
#         prompt = args.prompt
#         save_script = args.save_script
#         execute_script = args.execute_script

#         # Initialize the RAG system.
#         rag_system = NetUnicornRAG()
        
#         print(f"Sending prompt to RAG system: \"{prompt}\"")

#         code = rag_system.generate_code(prompt, save_script=save_script, execute_script=execute_script)
        
#         print("\\n--- Generated Code ---")
#         print(code)
#         print("----------------------\\n")

#     # except FileNotFoundError as e:
#     #     print(f"Error: {e}. Make sure your .env file (nl4netunicorn_llm/.env) and documentation JSON (nl4netunicorn_llm/data/netunicorn_docs.json) exist.")
#     except ValueError as e:
#         print(f"Configuration Error: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         import traceback
#         traceback.print_exc()

# if __name__ == '__main__':
#     main()
# nl4netunicorn_llm/examples/generate_netunicorn_script.py
import sys
import os
import logging
import argparse

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from nl4netunicorn_llm.src.netunicorn_rag import NetUnicornRAG

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
        parser = argparse.ArgumentParser(description='Generate netUnicorn Script')
        parser.add_argument('-p', '--prompt', dest='prompt', help='Prompt', type=str, required=True)
        parser.add_argument('-s', '--save_script', dest='save_script', help='Disable saving the generated script in a file', action='store_false')
        parser.add_argument('-f', '--feedback_loop', dest='feedback_loop', help='Disable feedback loop', action='store_false')
        parser.add_argument('-r', '--retries', dest='retries', help='Max number of retries', type=int)

        args = parser.parse_args()
        prompt = args.prompt
        save_script = args.save_script
        feedback_loop = args.feedback_loop
        retries = args.retries
        if not retries:
            results = rag_system.generate_code(
                user_prompt=prompt,
                save_final_script=save_script,
                enable_feedback_loop=feedback_loop
            )
        else:
            results = rag_system.generate_code(
                user_prompt=prompt,
                save_final_script=save_script,
                enable_feedback_loop=feedback_loop,
                max_retries=retries
            )
        print_results(results)
        # # Test Case 1: Feedback loop with default retries (3)
        # logger.info("\n--- Example 1: Generating with Feedback Loop (default max_retries=3) ---")
        # prompt1 = "Create a NetUnicorn script that connects to the server, selects one available node, and runs a sleep task for 10 seconds. Ensure all results are printed."
        # logger.info(f"Sending prompt to RAG system: \"{prompt1}\"")
        # results1 = rag_system.generate_code(
        #     user_prompt=prompt1,
        #     save_final_script=True,
        #     enable_feedback_loop=True # This is the default for generate_code, but explicit for clarity
        #     # max_retries will use the default of 3 from NetUnicornRAG
        # )
        # print_results(results1)

        # # Test Case 2: Generation only (no execution, no feedback beyond initial generation)
        # logger.info("\n--- Example 3: Generation Only (No Execution, No Retries) ---")
        # prompt3 = "Generate a NetUnicorn pipeline with a single SleepTask(10), ensuring all imports like RemoteClient, Pipeline, and SleepTask are present."
        # logger.info(f"Sending prompt to RAG system: \"{prompt3}\"")
        # results3 = rag_system.generate_code(
        #     user_prompt=prompt3,
        #     save_final_script=False, 
        #     enable_feedback_loop=False 
        # )
        # print_results(results3)
        # if results3.get('final_script_path') is not None:
        #     logger.error(f"Test Case 3 Error: Final script path was {results3.get('final_script_path')} but should be None when save_final_script is False.")
        
        # # Test Case 4: Prompt for ShellCommand
        # logger.info("\n--- Example 4: Prompt for ShellCommand (expect success) ---")
        # prompt4 = "Create a NetUnicorn script that runs a shell command 'echo Hello from ShellCommand'. Use ShellCommand from basic tasks."
        # logger.info(f"Sending prompt to RAG system: \"{prompt4}\"")
        # results4 = rag_system.generate_code(
        #     user_prompt=prompt4,
        #     save_final_script=True,
        #     enable_feedback_loop=True,
        #     max_retries=2 
        # )
        # print_results(results4)

        # logger.info("\n--- Example Script Finished ---")

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