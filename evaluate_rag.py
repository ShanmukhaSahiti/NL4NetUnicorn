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


def evaluate_rag(rag: NetUnicornRAG, prompts: list[str], out_path: str, save_script: bool, feedback_loop: bool, retries):
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
                if retries:
                    code = rag.generate_code(
                        user_prompt=prompt,
                        save_final_script=save_script,
                        enable_feedback_loop=feedback_loop,
                        max_retries=retries
                        )
                else:
                    code = rag.generate_code(
                        user_prompt=prompt,
                        save_final_script=save_script,
                        enable_feedback_loop=feedback_loop
                        )
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
    parser.add_argument('-s', '--save_script', dest='save_script', help='Disable saving the generated script in a file', action='store_false')
    parser.add_argument('-f', '--feedback_loop', dest='feedback_loop', help='Disable feedback loop', action='store_false')
    parser.add_argument('-r', '--retries', dest='retries', help='Max number of retries', type=int)

    args = parser.parse_args()
    input_file = args.file
    save_script = args.save_script
    feedback_loop = args.feedback_loop
    retries = args.retries

    labeled_prompts = parse_prompts(input_file)
    evaluate_rag(rag, labeled_prompts, out_file, save_script, feedback_loop, retries)
    print(f"Evaluation saved to: {out_file}")