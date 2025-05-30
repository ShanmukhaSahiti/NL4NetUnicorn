import re
from nl4netunicorn_llm.src.netunicorn_rag import NetUnicornRAG
from datetime import datetime
import os
import argparse

OUTPUT_DIR = "evaluation_reports"

def parse_prompts(file_path: str) -> list[str]:
    """
    Parses a plain text file where each line is a prompt.
    Returns a list of prompt strings.
    """
    prompts = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                prompts.append(line)
    return prompts


def evaluate_rag(rag: NetUnicornRAG, prompts: list[str], out_path: str):
    with open(out_path, "w") as f:
        f.write(f"# NetUnicorn RAG Evaluation Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        for prompt in prompts:
            f.write(f"Prompt: {prompt}\n\n")
        
            f.write("### Retrieved Context:\n")
            chunk_log = rag.log_retrieved_chunks(prompt, k=3)
            f.write(chunk_log + "\n")

            # Generate code
            try:
                code = rag.generate_code(prompt)
                f.write("### Generated Code:\n")
                f.write("```python\n" + code + "\n```\n\n")
            except Exception as e:
                f.write(f"Error generating code: {e}\n\n")

            f.write("---\n\n")

if __name__ == "__main__":
    rag = NetUnicornRAG()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = f"{OUTPUT_DIR}/rag_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    parser = argparse.ArgumentParser(description='Generating and Evaluating LLM-Generated Scripts')
    parser.add_argument('-i', '--input', dest='file', help='Prompts File: Each prompt should be in a new line', type=str, required=True)

    args = parser.parse_args()
    input_file = args.file
    labeled_prompts = parse_prompts(input_file)
    evaluate_rag(rag, labeled_prompts, out_file)
    print(f"Evaluation saved to: {out_file}")