import os
import json
import datetime
import logging 
import sys 
import traceback 
from dotenv import load_dotenv
from typing import Dict, Any 

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS 
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.documents import Document

from .script_executor import ScriptExecutor
from .feedback_handler import FeedbackHandler


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GENERATED_SCRIPTS_DIR = "nl4netunicorn_llm/generated_scripts" 
FEEDBACK_ATTEMPTS_DIR = "nl4netunicorn_llm/generated_scripts/feedback_attempts"


_INITIAL_SYSTEM_PROMPT_TEMPLATE = """
You are an expert Python programmer specializing in the NetUnicorn library.
Your task is to generate a complete, runnable NetUnicorn Python script based on the user's request and relevant NetUnicorn documentation context provided.
The script should interact with a NetUnicorn server using the provided credentials.

Context: {context}
User's request: {input}

Please generate the Python script adhering to the following guidelines:
1.  **Imports**: Ensure all necessary imports are at the top. This typically includes:
    - `import os` (if using environment variables for credentials, though they are injected here)
    - `import time`
    - `from pprint import pprint` (for readable result printing)
    - `from netunicorn.client.remote import RemoteClient, RemoteClientException`
    - `from netunicorn.base.experiment import Experiment, ExperimentStatus`
    - `from netunicorn.base.pipeline import Pipeline`
    - Specific task classes from `netunicorn.library.tasks.*` (e.g., `from netunicorn.library.tasks.basic import SleepTask`)
    - `from netunicorn.base.environment_definitions import ShellExecution` (or other environment definitions if needed)
    - `from returns.pipeline import is_successful`
    - `from returns.result import Result`
2.  **Credentials**: The script will use NetUnicorn credentials provided as Python variables (endpoint, login, password). Your generated code should use these directly.
    Your first lines of code in the script, after imports, should define these credentials like so, using the exact values provided to you:
    `NETUNICORN_ENDPOINT = "{endpoint}"`  # Actual endpoint value will be provided here
    `NETUNICORN_LOGIN = "{login}"`    # Actual login value will be provided here
    `NETUNICORN_PASSWORD = "{password}"` # Actual password value will be provided here
    Then, use these variables (`NETUNICORN_ENDPOINT`, `NETUNICORN_LOGIN`, `NETUNICORN_PASSWORD`) when initializing the `RemoteClient`.
    For example:
    `client = RemoteClient(endpoint=NETUNICORN_ENDPOINT, login=NETUNICORN_LOGIN, password=NETUNICORN_PASSWORD)`
3.  **Client Initialization**: Create a `RemoteClient` instance using the credentials: 
    `client = RemoteClient(endpoint=NETUNICORN_ENDPOINT, login=NETUNICORN_LOGIN, password=NETUNICORN_PASSWORD)`
    Optionally, you can include a health check: `print(f"Client Healthcheck: {{client.healthcheck()}}")`
4.  **Pipeline Creation**: Instantiate `pipeline = Pipeline()`. Add tasks using `pipeline.then(...)`. For example, `pipeline.then(SleepTask(10))`.
5.  **Node Selection**:
    *   Get all available nodes: `node_pool = client.get_nodes()`.
    *   Print available nodes for debugging if useful: `print(f"Available nodes: {{node_pool}}")`.
    *   Select working nodes. If specific filtering is requested, use `node_pool.filter(...)`. Otherwise, a common approach is `working_nodes = node_pool.take(1)`.
    *   **Crucially**: Check if `working_nodes` is empty. If so, print an informative message and exit, as an experiment cannot run on zero nodes.
        ```python
        if not working_nodes:
            print("No suitable working nodes found after filtering or take(1). Exiting.")
            exit()
        print(f"Selected working nodes: {{working_nodes}}")
        ```
6.  **Experiment Object and Definition**:
    *   Create an `Experiment` object and map the pipeline: `experiment = Experiment().map(pipeline, working_nodes)`.
    *   Set the environment definition, typically: `experiment.environment_definition = ShellExecution()` for general tasks.
7.  **Experiment Naming and Cleanup**:
    *   Define a unique `experiment_name`, e.g., by including a timestamp: `experiment_name = f"nl4nu_exp_{{time.strftime('%Y%m%d%H%M%S')}}"`.
    *   **Important**: Before preparing, attempt to delete any pre-existing experiment with the same name using the exact pattern below:
        ```python
        try:
            client.delete_experiment(experiment_name)
            print(f"Successfully deleted pre-existing experiment: {{experiment_name}}")
        except RemoteClientException:
            print(f"Info: Experiment '{{experiment_name}}' not found or couldn't be deleted (may not exist, this is not an error).")
        except Exception as e: # Catch other potential errors during deletion
            print(f"Warning: An unexpected error during experiment deletion for '{{experiment_name}}': {{e}}")
        ```
8.  **Experiment Lifecycle & Results**:
    *   **Prepare**: `client.prepare_experiment(experiment, experiment_name)`.
    *   **Poll for READY**: Loop, get `status_info = client.get_experiment_status(experiment_name)`, print `status_info.status`, and break when `status_info.status == ExperimentStatus.READY`. Use `time.sleep(SOME_SECONDS)` in the loop.
    *   Optionally, after READY, you can print deployment status: `prepared_exp = status_info.experiment; for dep in prepared_exp: print(f"Node: {{dep.node}}, Prepared: {{dep.prepared}}, Error: {{dep.error}}")`
    *   **Start Execution**: `client.start_execution(experiment_name)`.
    *   **Poll for FINISHED/Completion**: Loop, get `status_info = client.get_experiment_status(experiment_name)`, print `status_info.status`, and break when `status_info.status != ExperimentStatus.RUNNING`. Use `time.sleep(SOME_SECONDS)`.
    *   **Result Retrieval and Processing**: After polling indicates completion, get `final_status_info = client.get_experiment_status(experiment_name)`.
        Print overall status: `print(f"Final experiment status: {{final_status_info.status}}")`
        If `final_status_info.status == ExperimentStatus.FINISHED` and `final_status_info.execution_result`:
            print("Experiment Finished Successfully. Processing results:")
            # final_status_info.execution_result is a list of DeploymentExecutionResult objects
            for report in final_status_info.execution_result:
                print(f"--- Report for Node: {{report.node.name}} ---") # CRITICAL: Use report.node.name
                print(f"  Error (if any): {{report.error}}")
                actual_result_value, log_list = report.result # report.result is a tuple (value, list_of_log_strings)
                print(f"  Actual Result Type: {{type(actual_result_value)}}")
                if isinstance(actual_result_value, Result):
                    processed_value = actual_result_value.unwrap() if is_successful(actual_result_value) else actual_result_value.failure()
                    print(f"  Processed Result (from returns.Result):")
                    pprint.pprint(processed_value)
                else:
                    print(f"  Result (raw):")
                    pprint.pprint(actual_result_value)
                print(f"  Logs:")
                if log_list:
                    for log_entry in log_list:
                        print(f"    {{log_entry.strip()}}") # Iterate and print each log string
                else:
                    print("    (No logs reported for this task)")
                print("--- End Report ---")
        elif `final_status_info.status != ExperimentStatus.FINISHED`:
            print(f"Experiment did not finish successfully. Final status: {{final_status_info.status}}")
            if final_status_info.error:
                 print(f"Error details from final_status_info: {{final_status_info.error}}")
        else: # Status is FINISHED but no execution_result, or other conditions
            print(f"Experiment status is {{final_status_info.status}} but no execution results found or an issue occurred.")
9.  **Output Format**: Generate ONLY the Python code block. No explanatory text before or after.
10. **Pythonic Code**: Clean, readable, PEP8-compliant code.

Key script structure:
```python
# Imports (os, time, pprint, RemoteClient, RemoteClientException, Experiment, ExperimentStatus, Pipeline, specific tasks, ShellExecution, is_successful, Result)
# Credentials (will be defined in the script scope, use NETUNICORN_ENDPOINT, NETUNICORN_LOGIN, NETUNICORN_PASSWORD)
# Client Initialization (client = RemoteClient(...), client.healthcheck())
# Pipeline Definition (pipeline = Pipeline().then(...))
# Node Selection (client.get_nodes(), node_pool.take(1), check if working_nodes is empty, print selections)
# Experiment Creation (experiment = Experiment().map(...), experiment.environment_definition = ...)
# Experiment Naming (experiment_name = f"..._{{time.strftime(...)}}")
# Experiment Cleanup (try/except RemoteClientException for client.delete_experiment)
# Prepare Experiment (client.prepare_experiment)
# Poll for READY (while loop, client.get_experiment_status, check .status == ExperimentStatus.READY, time.sleep)
# Optional: Print deployment status from status_info.experiment
# Start Execution (client.start_execution)
# Poll for Completion (while loop, client.get_experiment_status, check .status != ExperimentStatus.RUNNING, time.sleep)
# Process Results (get final_status_info, check .status, iterate .execution_result, use report.node.name, unpack report.result, handle returns.Result with is_successful/unwrap/failure, print logs from log_list)
```
The user request is: {input}
Generate the full Python script now.
"""

_RETRY_SYSTEM_PROMPT_TEMPLATE = """
You are an expert Python programmer specializing in the NetUnicorn library.
Your task is to correct a previously generated NetUnicorn Python script based on execution feedback.
The original user request was: {original_request}
The relevant documentation context (if any was used for the previous attempt) is:
<context>
{context}
</context>

The PREVIOUSLY generated script was:
```python
{previous_code}
```

When this script was executed, it produced the following output:
STDOUT:
```text
{execution_stdout}
```
STDERR:
```text
{execution_stderr}
```

Analyze the STDERR for errors. If no errors, analyze STDOUT to see if the script achieved the user's goal based on the original request.
If there are errors in STDERR or the STDOUT does not indicate success:
1. Identify the cause of the error or failure.
2. Generate a new, complete, and runnable Python script that fixes the identified issues.
3. Ensure the corrected script still adheres to all best practices for NetUnicorn as outlined below and in the initial prompt style.
4. Pay close attention to the specific error messages in STDERR.
5. **Experiment Naming**: If you regenerate the experiment naming part, ensure it remains unique, ideally by using a timestamp: `experiment_name = f"nl4nu_exp_{{time.strftime('%Y%m%d%H%M%S')}}"`.
6. **Result Processing Details**: If modifying result processing, strictly follow this pattern:
   - `final_status_info.execution_result` is a list of reports. Iterate over it directly (e.g., `for report in final_status_info.execution_result:`).
   - Node name is `report.node.name`.
   - Task result and logs are in `report.result` which is a tuple: `actual_result_value, log_list = report.result`.
   - If `actual_result_value` is a `returns.result.Result` object, use `is_successful(actual_result_value)` and then `actual_result_value.unwrap()` or `actual_result_value.failure()`.
   - Print logs by iterating through `log_list`.
   - Ensure `pprint`, `Result`, `is_successful` and all other necessary NetUnicorn classes are imported at the top of the script.
7. **Experiment Cleanup**: Ensure the experiment cleanup uses `try...except RemoteClientException: print(...)` specifically for `client.delete_experiment`.
8.  **Credentials**: Ensure the corrected script defines and uses the NetUnicorn credentials at the top, like so, using the exact values provided:
    `NETUNICORN_ENDPOINT = "{endpoint}"`  # Actual endpoint value will be provided here
    `NETUNICORN_LOGIN = "{login}"`    # Actual login value will be provided here
    `NETUNICORN_PASSWORD = "{password}"` # Actual password value will be provided here
    Then, use these variables for the `RemoteClient`.
    For example:
    `client = RemoteClient(endpoint=NETUNICORN_ENDPOINT, login=NETUNICORN_LOGIN, password=NETUNICORN_PASSWORD)`

If STDOUT indicates success and STDERR is empty or non-critical, and you believe the script fulfilled the original request, you can either:
    a) State that the previous code was correct by responding with "PREVIOUS_CODE_CORRECT".
    b) Re-generate the *exact same script* if you are highly confident.

Generate ONLY the Python code block for the corrected script. Do not include any explanatory text before or after the code block.
If you believe the previous code was correct and no changes are needed, respond with the special string "PREVIOUS_CODE_CORRECT" instead of a script.

Corrected Python script or "PREVIOUS_CODE_CORRECT":
"""

class NetUnicornRAG:
    def __init__(self, docs_path="nl4netunicorn_llm/data/netunicorn_docs.json", generated_scripts_dir=None):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")

        self.netunicorn_endpoint = os.getenv("NETUNICORN_ENDPOINT")
        self.netunicorn_login = os.getenv("NETUNICORN_LOGIN")
        self.netunicorn_password = os.getenv("NETUNICORN_PASSWORD")
        if not all([self.netunicorn_endpoint, self.netunicorn_login, self.netunicorn_password]):
            raise ValueError("NetUnicorn credentials not found. Ensure .env is in the project root.")

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        self.generated_scripts_base_path = os.path.join(project_root, generated_scripts_dir or GENERATED_SCRIPTS_DIR)
        self.feedback_attempts_path = os.path.join(project_root, FEEDBACK_ATTEMPTS_DIR)

        os.makedirs(self.generated_scripts_base_path, exist_ok=True)
        os.makedirs(self.feedback_attempts_path, exist_ok=True)
        
        logging.info(f"Generated scripts will be saved in: {self.generated_scripts_base_path}")
        logging.info(f"Feedback attempt scripts will be saved in: {self.feedback_attempts_path}")

        self.llm = ChatOpenAI(openai_api_key=self.openai_api_key, model_name="gpt-3.5-turbo", temperature=0.0)
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)

        if not os.path.isabs(docs_path):
            docs_path = os.path.join(project_root, docs_path if docs_path.startswith("nl4netunicorn_llm/") else os.path.join("nl4netunicorn_llm", docs_path))
        
        self.docs = self._load_documents(docs_path)
        self.vector_store = self._create_vector_store(self.docs)
        
        self.initial_rag_chain = self._setup_initial_rag_chain()
        self.feedback_rag_chain = self._setup_feedback_rag_chain()
        
        self.script_executor = ScriptExecutor()

    def _load_documents(self, path: str) -> list[Document]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            raise FileNotFoundError(f"Doc file not found: {path}. Project root: {project_root}")
        except json.JSONDecodeError:
            raise ValueError(f"Error decoding JSON: {path}")
        return [Document(page_content=item['content'], metadata={"source": item['source']}) for item in data]

    def _create_vector_store(self, documents: list[Document]):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        split_documents = text_splitter.split_documents(documents)
        if not split_documents:
            if documents and any(doc.page_content for doc in documents):
                split_documents = documents 
            else:
                logging.warning("No processable content for vector store. Retriever might not find context.")
                return FAISS.from_texts(["placeholder for empty faiss index to avoid error"], self.embeddings)
        return FAISS.from_documents(split_documents, self.embeddings)

    def _strip_markdown(self, code: str) -> str:
        code = code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        elif code.startswith("```"):
            code = code[len("```"):].strip()
        if code.endswith("```"):
            code = code[:-len("```")].strip()
        return code

    def _setup_initial_rag_chain(self):
        retriever = self.vector_store.as_retriever()
        prompt = ChatPromptTemplate.from_template(_INITIAL_SYSTEM_PROMPT_TEMPLATE)
        combine_docs_chain = create_stuff_documents_chain(self.llm, prompt)
        return create_retrieval_chain(retriever, combine_docs_chain)

    def _setup_feedback_rag_chain(self):
        retriever = self.vector_store.as_retriever()
        prompt = ChatPromptTemplate.from_template(_RETRY_SYSTEM_PROMPT_TEMPLATE)
        feedback_document_chain = create_stuff_documents_chain(self.llm, prompt)
        return create_retrieval_chain(retriever, feedback_document_chain)


    def _generate_code_initial(self, user_prompt: str, credentials: Dict[str, str]) -> str:
        logging.info(f"RAG: Initial generation for prompt: \"{user_prompt[:100]}...\"")
        response = self.initial_rag_chain.invoke({
            "input": user_prompt,
            "endpoint": credentials["endpoint"],
            "login": credentials["login"],
            "password": credentials["password"]
        })
        generated_code = response.get("answer", "")
        if not generated_code:
            logging.error("RAG: Initial generation returned no code/answer.")
            raise ValueError("LLM did not return any code for the initial prompt.")
        return self._strip_markdown(generated_code)

    def _generate_code_with_feedback(self, original_request: str, previous_code: str, 
                                     execution_stdout: str, execution_stderr: str, 
                                     credentials: Dict[str, str]) -> str:
        logging.info(f"RAG: Generating with feedback for request: \"{original_request[:100]}...\"")
        
        response = self.feedback_rag_chain.invoke({
            "input": original_request, 
            "original_request": original_request, 
            "previous_code": previous_code,
            "execution_stdout": execution_stdout,
            "execution_stderr": execution_stderr,
            "endpoint": credentials["endpoint"],
            "login": credentials["login"],
            "password": credentials["password"]
        })
        corrected_code = response.get("answer", "")
        
        if not corrected_code:
            logging.error("RAG: Feedback generation returned no code/answer.")
            raise ValueError("LLM did not return any code during feedback generation.")

        if corrected_code.strip() == "PREVIOUS_CODE_CORRECT":
            logging.info("RAG: LLM indicated previous code was correct.")
            return previous_code 

        return self._strip_markdown(corrected_code)

    def _get_final_save_path(self, user_prompt: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        sane_prompt = "".join(c if c.isalnum() or c.isspace() else "" for c in user_prompt)
        sane_prompt = sane_prompt.replace(" ", "_")[:50]
        filename = f"nu_script_final_{timestamp}_{sane_prompt}.py"
        return os.path.join(self.generated_scripts_base_path, filename)

    def generate_code(self, user_prompt: str, 
                      save_final_script: bool = True, 
                      enable_feedback_loop: bool = True, # Default to True
                      max_retries: int = 3) -> Dict[str, Any]: # Default to 3
        if not user_prompt:
            raise ValueError("User prompt cannot be empty.")

        credentials = {
            "endpoint": self.netunicorn_endpoint,
            "login": self.netunicorn_login,
            "password": self.netunicorn_password
        }
        
        intended_final_script_path = None
        if save_final_script:
            intended_final_script_path = self._get_final_save_path(user_prompt)
            os.makedirs(os.path.dirname(intended_final_script_path), exist_ok=True)

        effective_max_retries = max_retries if enable_feedback_loop else 0
        
        logging.info(f"RAG: Starting generation. Feedback enabled: {enable_feedback_loop}, Max retries: {effective_max_retries}")
        
        feedback_handler = FeedbackHandler(
            initial_code_generator=self._generate_code_initial,
            feedback_code_generator=self._generate_code_with_feedback,
            script_executor=self.script_executor,
            max_retries=effective_max_retries, 
            netunicorn_credentials=credentials
        )
        
        final_script_override_name = os.path.basename(intended_final_script_path) if intended_final_script_path else None
        
        result = feedback_handler.run_generation_with_feedback(
            user_prompt,
            save_script_base_path=self.feedback_attempts_path, 
            final_script_name_override=final_script_override_name 
        )

        final_script_generated_path = result.get("final_script_path")

        if save_final_script and intended_final_script_path and final_script_generated_path:
            if os.path.abspath(final_script_generated_path) != os.path.abspath(intended_final_script_path):
                try:
                    with open(final_script_generated_path, "r", encoding="utf-8") as source_file:
                        with open(intended_final_script_path, "w", encoding="utf-8") as dest_file:
                            dest_file.write(source_file.read())
                    
                    log_message_verb = "Copied successful" if result["success"] else "Copied last attempted"
                    logging.info(f"{log_message_verb} script from {final_script_generated_path} to {intended_final_script_path}")
                    result['final_script_path'] = intended_final_script_path # Update result to point to the RAG's intended path
                except IOError as e:
                    logging.error(f"Error copying script to final destination: {e}. Script remains at: {final_script_generated_path}")
        elif not save_final_script and final_script_generated_path:
            if self.feedback_attempts_path in os.path.abspath(final_script_generated_path):
                try:
                    if not (intended_final_script_path and os.path.abspath(final_script_generated_path) == os.path.abspath(intended_final_script_path)):
                        os.remove(final_script_generated_path)
                        logging.info(f"Not saving final script, removed temporary script: {final_script_generated_path}")
                        if 'final_script_path' in result:
                           result['final_script_path'] = None
                except OSError as e:
                    logging.warning(f"Could not remove temporary script {final_script_generated_path}: {e}")
            result['final_script_path'] = None


        logging.info(f"RAG: Processing finished. Success: {result['success']}. Final script path: {result.get('final_script_path')}")
        return result

    def log_retrieved_chunks(self, user_prompt: str, k: int = 3) -> str:
        logging.info(f"RAG: Retrieving chunks for prompt: \"{user_prompt[:100]}...\"")
        retriever = self.vector_store.as_retriever()
        try:
            retrieved_docs = retriever.invoke(user_prompt) 
        except Exception as e:
            logging.error(f"Error during document retrieval for logging: {e}")
            return f"Error retrieving documents: {e}"

        log_lines = [f"Retrieved Context Chunks for: \"{user_prompt}\"\n"]
        if not retrieved_docs:
            log_lines.append("No documents retrieved.")
        for i, doc in enumerate(retrieved_docs[:k]):
            source = doc.metadata.get('source', 'unknown')
            content_preview = doc.page_content.strip()[:300].replace('\n', ' ') 
            log_lines.append(f"Chunk {i+1} (source: {source}): \n")
            log_lines.append(f"```\n{content_preview}...\n```\n")
        return "\n".join(log_lines)