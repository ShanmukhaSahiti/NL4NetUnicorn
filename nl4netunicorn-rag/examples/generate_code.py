import os
from dotenv import load_dotenv
from ..src.rag_system import NetUnicornRAG

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize RAG system
    rag = NetUnicornRAG()
    
    # Example prompts
    prompts = [
        "Create a script to run a speed test experiment on Raspberry Pi nodes",
        "Create a script to stream video between two nodes",
        "Create a script to collect network statistics from multiple nodes"
    ]
    
    # Generate code for each prompt
    for i, prompt in enumerate(prompts, 1):
        print(f"\nGenerating code for prompt {i}: {prompt}")
        try:
            code = rag.generate_code(prompt)
            
            # Save to file
            output_file = f"generated_script_{i}.py"
            with open(output_file, "w") as f:
                f.write(code)
            print(f"Code saved to {output_file}")
            
        except Exception as e:
            print(f"Error generating code for prompt {i}: {str(e)}")

if __name__ == "__main__":
    main() 