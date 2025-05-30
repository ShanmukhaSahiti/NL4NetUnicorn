# nl4netunicorn_llm/examples/generate_netunicorn_script.py
import sys
import os
import argparse

from netunicorn_rag import NetUnicornRAG

def main():
    try:
        # Parse arguments
        parser = argparse.ArgumentParser(description='Generate netUnicorn Script')
        parser.add_argument('-p', '--prompt', dest='prompt', help='Prompt', type=str, required=True)
        parser.add_argument('-s', '--save_script', dest='save_script', help='Save the generated script in a file', action='store_true')
        parser.add_argument('-e', '--execute_script', dest='execute_script', help='Execute the generated script', action='store_true')

        args = parser.parse_args()
        prompt = args.prompt
        save_script = args.save_script
        execute_script = args.execute_script

        # Initialize the RAG system.
        rag_system = NetUnicornRAG()
        
        print(f"Sending prompt to RAG system: \"{prompt}\"")

        code = rag_system.generate_code(prompt, save_script=save_script, execute_script=execute_script)
        
        print("\\n--- Generated Code ---")
        print(code)
        print("----------------------\\n")

    # except FileNotFoundError as e:
    #     print(f"Error: {e}. Make sure your .env file (nl4netunicorn_llm/.env) and documentation JSON (nl4netunicorn_llm/data/netunicorn_docs.json) exist.")
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 