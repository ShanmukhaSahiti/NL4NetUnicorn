import argparse
import os
import sys
import logging
from dotenv import load_dotenv
import re

# Ensure the project root is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir # Assuming this script is in the project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from nl4netunicorn_llm.src.netunicorn_rag import NetUnicornRAG
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_retrieved_docs_for_judge(retrieved_docs: list[Document]) -> str:
    """Formats retrieved documents for presentation to the LLM judge."""
    if not retrieved_docs:
        return "No documents retrieved."
    
    formatted_output = []
    for i, doc in enumerate(retrieved_docs):
        source = doc.metadata.get('source', 'unknown source')
        content_preview = doc.page_content.strip().replace('\n', ' ')
        formatted_output.append(f"Chunk {i+1} (Source: {source}):\n{content_preview}\n---")
    return "\n".join(formatted_output)

def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG context aptness using an LLM judge.")
    parser.add_argument("-p", "--prompt", type=str, required=True, help="The user's natural language prompt.")
    parser.add_argument(
        "--docs_path", 
        type=str, 
        default="nl4netunicorn_llm/data/netunicorn_docs.json", 
        help="Path to the NetUnicorn documentation JSON file (context source)."
    )
    parser.add_argument(
        "--judge_model_name", 
        type=str, 
        default="gpt-3.5-turbo", # Sensible default
        help="The model name for the LLM judge (e.g., gpt-3.5-turbo, gpt-4)."
    )
    parser.add_argument(
        "-k", 
        "--num_chunks", 
        type=int, 
        default=3, 
        help="Number of top context chunks to retrieve and show to the judge."
    )
    
    args = parser.parse_args()

    logger.info("Starting context aptness evaluation...")
    logger.info(f"User Prompt: {args.prompt}")
    logger.info(f"Number of chunks to retrieve: {args.num_chunks}")
    logger.info(f"LLM Judge Model: {args.judge_model_name}")

    # Load environment variables (e.g., OPENAI_API_KEY)
    # NetUnicornRAG constructor also calls load_dotenv, but good to ensure it's loaded.
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Loaded .env file from: {env_path}")
    else:
        logger.warning(f".env file not found at {env_path}. Make sure OPENAI_API_KEY is set in your environment.")

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY is not set. Please set it in your .env file or environment variables.")
        return

    try:
        # Initialize NetUnicornRAG to use its retriever
        # The docs_path in RAG's __init__ will be used if it's different from default.
        # Make sure the docs_path is correctly resolved relative to project_root if not absolute.
        rag_docs_path = args.docs_path
        if not os.path.isabs(rag_docs_path):
            rag_docs_path = os.path.join(project_root, rag_docs_path)
        
        logger.info(f"Initializing NetUnicornRAG with docs path: {rag_docs_path}")
        rag_system = NetUnicornRAG(docs_path=rag_docs_path)
        
        # Retrieve context chunks
        logger.info(f"Retrieving top {args.num_chunks} context chunks for the prompt...")
        retriever = rag_system.vector_store.as_retriever(search_kwargs={"k": args.num_chunks})
        retrieved_docs = retriever.invoke(args.prompt) # Returns a list of Document objects

        if not retrieved_docs:
            logger.warning("No context chunks were retrieved for the given prompt.")
            formatted_chunks_for_judge = "No documents retrieved."
        else:
            logger.info(f"Successfully retrieved {len(retrieved_docs)} chunks.")
            formatted_chunks_for_judge = format_retrieved_docs_for_judge(retrieved_docs)

        # Initialize the LLM Judge
        logger.info(f"Initializing LLM Judge with model: {args.judge_model_name}...")
        judge_llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"), 
            model_name=args.judge_model_name, 
            temperature=0.1 # Low temperature for more deterministic evaluation
        )

        # Create the master prompt for the LLM Judge
        judge_master_prompt = f"""
You are an expert evaluator for Retrieval Augmented Generation (RAG) systems.
Your task is to assess if the provided "Retrieved Context" is relevant, sufficient, and helpful for an LLM to generate a NetUnicorn script based on the "Original User Prompt".

Original User Prompt:
---
{args.prompt}
---

Retrieved Context:
---
{formatted_chunks_for_judge}
---

Please provide your evaluation focusing on these aspects:
1.  **Relevance**: Is each piece of context directly related to the user's request? Point out any irrelevant chunks.
2.  **Sufficiency**: Does the context, as a whole, contain enough information for an LLM to successfully and completely address the user's prompt? Identify any key missing pieces of information that should have been retrieved.
3.  **Helpfulness**: Overall, how helpful would this context be for an LLM to generate the correct NetUnicorn script? Would it guide the LLM effectively or potentially mislead it?
4.  **Overall Assessment & Suggestions**: Concisely state if the retrieved context is Good, Adequate, or Poor. If not Good, suggest what kind of information is missing or what could be improved in the retrieval.


Finally, end your evaluation with scores for each of the 4 aspects, on a scale of 0-5, where 0 is the worst and 5 is the best. For this, give the scores in the following format: 
<scores>
    Relevance: <score_1>
    Sufficiency: <score_2>
    Helpfulness: <score_3>
    Overall: <score_4>
</scores>

Provide your evaluation as a structured response.
"""
        
        logger.info("Sending request to LLM Judge...")
        judge_assessment_response = judge_llm.invoke(judge_master_prompt)
        judge_assessment = judge_assessment_response.content
        extracted_scores = re.search(r'<scores>(.*?)</scores>', judge_assessment, re.DOTALL)
        if extracted_scores:
            scores = extracted_scores.group(1)
        else:
            scores = "No scores found in the response."

        logger.info("Received assessment from LLM Judge.")

        # Print the results
        print("\n" + "="*80)
        print("LLM JUDGE CONTEXT APTNESS EVALUATION")
        print("="*80)
        print(f"\nOriginal User Prompt:\n---\n{args.prompt}\n---")
        print(f"\nRetrieved Context (Top {args.num_chunks} chunks shown to judge):\n---\n{formatted_chunks_for_judge}\n---")
        print(f"\nLLM Judge's Assessment (Model: {args.judge_model_name}):\n---\n{judge_assessment}\n---")
        print("="*80)
        print(f"\nScores:\n---\n{scores}\n---")

    except FileNotFoundError as e:
        logger.error(f"ERROR: A required file was not found. {e}. Ensure documentation JSON exists and paths are correct.")
        logger.error(f"Attempted to load docs from: {rag_docs_path if 'rag_docs_path' in locals() else args.docs_path}")
    except ValueError as e:
        logger.error(f"ERROR: A value error occurred. This might be due to missing API keys or invalid configuration. {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main() 