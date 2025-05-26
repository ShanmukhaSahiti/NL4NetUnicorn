import re
from nl4netunicorn_llm.src.netunicorn_rag import NetUnicornRAG
from datetime import datetime
import os

PROMPT_FILE = "nl4netunicorn_llm/examples/example_prompts.txt"
OUTPUT_DIR = "evaluation_reports"

def parse_prompts(file_path: str) -> list[tuple[str, str]]:
    """
    Parses a prompt text file into a list of (label, prompt) pairs.
    Expected format:
    1. Section Name:
       - "prompt goes here"
    """
    prompts = []
    with open(file_path, "r") as f:
        raw = f.read()

    sections = re.findall(r'(\d+)\.\s+(.+?):\s+-\s+"([^"]+)"', raw)
    for num, label, prompt in sections:
        prompts.append((f"{num}. {label.strip()}", prompt.strip()))
    return prompts

def evaluate_rag(rag: NetUnicornRAG, labeled_prompts: list[tuple[str, str]], out_path: str):
    with open(out_path, "w") as f:
        f.write(f"# NetUnicorn RAG Evaluation Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        for label, prompt in labeled_prompts:
            f.write(f"## {label}\n")
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
    labeled_prompts = parse_prompts(PROMPT_FILE)
    evaluate_rag(rag, labeled_prompts, out_file)
    print(f"Evaluation saved to: {out_file}")