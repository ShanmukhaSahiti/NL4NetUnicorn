import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "nl4netunicorn-rag"))

from nl4netunicorn_llm.src.netunicorn_rag import NetUnicornRAG
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    # Initialize the RAG system
    rag = NetUnicornRAG()
    
    # Test prompt
    prompt = """
    Create a simple netunicorn experiment that:
    1. Sets up a basic network topology with 3 nodes
    2. Configures each node with a simple ping test
    3. Runs the experiment and collects results
    4. Saves the results to a file
    """
    
    try:
        # Generate code
        generated_code = rag.generate_code(prompt)
        
        # Print the generated code
        print("\nGenerated Code:")
        print("=" * 80)
        print(generated_code)
        print("=" * 80)
        
    except Exception as e:
        logging.error(f"Error during code generation: {str(e)}")

if __name__ == "__main__":
    main() 