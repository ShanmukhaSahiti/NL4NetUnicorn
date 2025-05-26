# nl4netunicorn_llm/examples/generate_netunicorn_script.py
import sys
import os

from nl4netunicorn_llm.src.netunicorn_rag import NetUnicornRAG

def main():
    try:
        # Initialize the RAG system. 
        # NetUnicornRAG will look for .env and data/netunicorn_docs.json 
        # in the nl4netunicorn_llm/ directory (relative to CWD, which should be NL4NetUnicorn/).
        rag_system = NetUnicornRAG()
        #prompt = "Create a NetUnicorn script that connects to the server, selects one available node, and runs a sleep task for 10 seconds."
        #prompt = "Create a NetUnicorn script to run an Ookla speed test on one available node and print the results."
        prompt = "Generate a script that first creates a small text file named 'upload_test.txt' with some sample text on one node. Then, upload this file to file.io with a 1-day expiration. Print the file.io link from the result."
        print(f"Sending prompt to RAG system: \"{prompt}\"")
        # Example: save the script but do not execute it by default
        code = rag_system.generate_code(prompt, save_script=True, execute_script=False)
        
        print("\\n--- Generated Code ---")
        print(code)
        print("----------------------\\n")

    except FileNotFoundError as e:
        print(f"Error: {e}. Make sure your .env file (nl4netunicorn_llm/.env) and documentation JSON (nl4netunicorn_llm/data/netunicorn_docs.json) exist.")
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 