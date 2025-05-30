import os
import json
import datetime # Added for timestamp in filename
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS 
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

GENERATED_SCRIPTS_DIR = "nl4netunicorn_llm/generated_scripts"

class NetUnicornRAG:
    def __init__(self, docs_path="nl4netunicorn_llm/data/netunicorn_docs.json"):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env")) # Look for .env in project root

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")

        self.netunicorn_endpoint = os.getenv("NETUNICORN_ENDPOINT")
        self.netunicorn_login = os.getenv("NETUNICORN_LOGIN")
        self.netunicorn_password = os.getenv("NETUNICORN_PASSWORD")
        if not all([self.netunicorn_endpoint, self.netunicorn_login, self.netunicorn_password]):
            raise ValueError("NetUnicorn credentials not found in environment variables. Ensure .env is in the project root.")

        # Create directory for generated scripts if it doesn't exist
        # Make GENERATED_SCRIPTS_DIR relative to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.generated_scripts_path = os.path.join(project_root, GENERATED_SCRIPTS_DIR)

        if not os.path.exists(self.generated_scripts_path):
            os.makedirs(self.generated_scripts_path)
            print(f"Created directory: {self.generated_scripts_path}")


        self.llm = ChatOpenAI(openai_api_key=self.openai_api_key, model_name="gpt-3.5-turbo", temperature=0)
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)

        # Adjust docs_path to be relative to project root if it's a relative path
        if not os.path.isabs(docs_path) and not docs_path.startswith("nl4netunicorn_llm/"):
             # Assuming docs_path like "data/netunicorn_docs.json" is relative to nl4netunicorn_llm
            docs_path = os.path.join(project_root, "nl4netunicorn_llm", docs_path)
        elif not os.path.isabs(docs_path) and docs_path.startswith("nl4netunicorn_llm/"):
            docs_path = os.path.join(project_root, docs_path)


        self.docs = self._load_documents(docs_path)
        self.vector_store = self._create_vector_store(self.docs)
        self.rag_chain = self._setup_rag_chain()

    def _load_documents(self, path: str) -> list[Document]:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Doc file not found: {path}. Please ensure it's correctly placed, e.g., nl4netunicorn_llm/data/netunicorn_docs.json relative to project root.")
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
                raise ValueError("No processable content for vector store.")
        return FAISS.from_documents(split_documents, self.embeddings)

    def _setup_rag_chain(self):
        retriever = self.vector_store.as_retriever()
        system_prompt = ('''
        You are an expert Python programmer specializing in the NetUnicorn library.
        Your task is to generate a complete, runnable NetUnicorn Python script based on the user's request and relevant NetUnicorn documentation context provided.
        The script should interact with a NetUnicorn server using the provided credentials.

        Context: {context}
        User's request: {input}

        Please generate the Python script adhering to the following guidelines:
        1.  **Complete and Runnable Script**: Ensure the script includes all necessary imports (primarily from `netunicorn.client.remote.RemoteClient`, `netunicorn.base.pipeline.Pipeline`, `netunicorn.library.tasks.*`, `netunicorn.base.experiment.Experiment`, `netunicorn.base.architecture.Architecture`, `netunicorn.base.deployment.Deployment`, `netunicorn.base.environment_definitions.DockerImage`, `netunicorn.base.environment_definitions.ShellExecution`, and `netunicorn.base.nodes.NodePool` if filtering by specific node properties. Also include `from netunicorn.client.remote import RemoteClientException` and `from netunicorn.base.experiment import ExperimentStatus` and `import time` for polling status.).
        2.  **Credentials**: Use these NetUnicorn credentials for `RemoteClient` (they will be injected into the script):
            Endpoint: `{endpoint}`
            Login: `{login}`
            Password: `{password}`
        3.  **Client Initialization**: Create a `RemoteClient` instance with the provided credentials. `client = RemoteClient(endpoint=\"{endpoint}\", login=\"{login}\", password=\"{password}\")`.
        4.  **Pipeline Creation**:
            *   Instantiate `Pipeline()`: `pipeline = Pipeline()`.
            *   Add tasks to the pipeline using the `.then()` method. For example: `pipeline.then(SleepTask(10))`.
            *   If the user requests a specific task, use that task. Otherwise, default to `SleepTask(5)`.
        5.  **Node Selection**:
            *   Get all available nodes using `client.get_nodes()`. Store in `node_pool = client.get_nodes()`.
            *   Filter nodes if specified in the request. If not, select one available node: `working_nodes = node_pool.take(1)`. 
            *   Ensure `working_nodes` is a list-like structure suitable for the experiment.
        6.  **Experiment Object and Definition**:
            *   Create an `Experiment` object: `experiment = Experiment()`.
            *   Define an `environment_definition`. For simple shell commands or Python tasks that don't need special docker images, use `ShellExecution()`: `experiment.environment_definition = ShellExecution()`
            *   Map the pipeline to nodes using the experiment object: `experiment.map(pipeline, working_nodes)`
        7.  **Experiment Naming and Cleanup**:
            *   Use a unique string for the experiment name, for example, `experiment_name = "nl4netunicorn_experiment_timestamp"`, where timestamp is generated using the python time package.
            *   Before preparing, attempt to delete any pre-existing experiment with the same name:
                ```python
                try:
                    client.delete_experiment(experiment_name)
                    print(f"Successfully deleted pre-existing experiment: {{experiment_name}}")
                except RemoteClientException as e:
                    print(f"Info: Could not delete experiment {{experiment_name}} (may not exist or already deleted): {{e}}")
                except Exception as e: # Catch any other potential exceptions during deletion
                    print(f"Warning: An unexpected error occurred while trying to delete experiment {{experiment_name}}: {{e}}")
                ```
        8.  **Experiment Lifecycle & Results**:
            *   Prepare the experiment: `client.prepare_experiment(experiment, experiment_name)`
            *   Poll for READY status:
                ```python
                print(f"Experiment {{experiment_name}} prepared. Waiting for readiness...")
                while True:
                    status = client.get_experiment_status(experiment_name).status
                    print(f"Current status: {{status}}")
                    if status == ExperimentStatus.READY:
                        print("Experiment is READY.")
                        break
                    time.sleep(10) # Poll every 10 seconds
                ```
            *   Start the experiment execution: `client.start_execution(experiment_name)`
            *   Wait for the experiment to complete (poll for FINISHED status):
                ```python
                print(f"Experiment {{experiment_name}} started. Waiting for completion...")
                while True:
                    status = client.get_experiment_status(experiment_name).status
                    print(f"Current status: {{status}}")
                    if status != ExperimentStatus.RUNNING:
                        break
                    time.sleep(20) # Poll every 20 seconds
                ```
            *   Retrieve and print results if FINISHED:
                ```python
                from returns.pipeline import is_successful
                from returns.result import Result
                final_status_info = client.get_experiment_status(experiment_name)
                if final_status_info.status == ExperimentStatus.FINISHED:
                    results = final_status_info.execution_result
                    print(f"Experiment results: {{results}}")
                    if results:
                        for report in results:
                            print(f"Node name: {{report.node.name}}")
                            print(f"Error: {{report.error}}")

                            result, log = report.result  # report stores results of execution and corresponding log
                            
                            # result is a returns.result.Result object, could be Success of Failure
                            print(type(result))
                            if isinstance(result, Result):
                                data = result.unwrap() if is_successful(result) else result
                                pprint(data)
                else:
                    print(f"Experiment did not finish successfully. Final status: {{final_status_info.status}}")
                    if final_status_info.error:
                         print(f"Error: {{final_status_info.error}}")

                ```
        9.  **Output Format**: Generate only the Python code block. Do not include any explanatory text before or after the code block. The script should be directly runnable.
        10. **Imports**: Ensure all necessary imports are at the top of the script. This includes `RemoteClient`, `Pipeline`, task-specific classes (e.g., `SleepTask`), `Experiment`, `ShellExecution` (or other env definitions), `ExperimentStatus`, `RemoteClientException`, and `time`.
        11. **Pythonic Code**: Write clean, readable, and pythonic code.
        Remember to use the specific method `experiment.map(pipeline, nodes)` AFTER `experiment = Experiment()` and `experiment.environment_definition = ShellExecution()` (or other definition).
        Do NOT use `client.create_experiment()`. Use `client.prepare_experiment(experiment_object, experiment_name_string)`.
        Do NOT use `experiment.wait_for_status()`, `experiment.start_execution()`, or `experiment.get_result()`. Use `client.get_experiment_status()` for polling and `client.start_execution()` to start the experiment.
        Polling `client.get_experiment_status()` is the preferred way to check if an experiment is READY and then if it has FINISHED. This provides more feedback during execution.
        Pay close attention to the full lifecycle: cleanup -> prepare -> poll for READY -> start -> poll for FINISHED -> process results.
        Make sure the experiment name is unique, potentially by adding a timestamp or a UUID to `experiment_name = "my_experiment_..."`.
        The experiment object should be passed to `client.prepare_experiment`, not the pipeline and nodes directly.
        Script structure:
        ```python
        # Imports
        # Credentials (will be injected)
        # Client
        # Pipeline
        # Nodes
        # Experiment object creation
        # Environment definition (e.g., ShellExecution)
        # Experiment mapping (experiment.map(pipeline, nodes))
        # Experiment name (unique)
        # Delete old experiment (try/except)
        # Prepare experiment
        # Poll for READY
        # Start experiment
        # Poll for FINISHED
        # Get and print results
        ```
        Ensure that `working_nodes` is used when mapping the experiment: `experiment.map(pipeline, working_nodes)`.
        The endpoint, login, and password are: {endpoint}, {login}, {password}
        The user request is: {input}
        Generate the full Python script now.
        ''')
        prompt = ChatPromptTemplate.from_messages([("system", system_prompt)])
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        return create_retrieval_chain(retriever, question_answer_chain)

    def generate_code(self, user_prompt: str, save_script: bool = True, execute_script: bool = False) -> str:
        if not user_prompt:
            raise ValueError("User prompt cannot be empty.")
        
        # Add a timestamp to the prompt for the experiment name, if not already specific
        # This helps ensure unique experiment names if the user prompt is generic
        # However, let the LLM handle the exact naming based on the refined prompt instructions.
        
        response = self.rag_chain.invoke({
            "input": user_prompt, 
            "endpoint": self.netunicorn_endpoint,
            "login": self.netunicorn_login,
            "password": self.netunicorn_password
        })
        generated_code = response.get("answer", "")
        
        # Strip markdown fences
        if generated_code.startswith("```python"):
            generated_code = generated_code[len("```python"):].strip()
        elif generated_code.startswith("```"): # Handle cases where just ``` is used
            generated_code = generated_code[len("```"):].strip()
        
        if generated_code.endswith("```"):
            generated_code = generated_code[:-len("```")].strip()

        if save_script:
            try:
                # Create a sanitized filename from the prompt and a timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # Sanitize prompt for filename: keep alphanumeric, replace spaces with underscores, truncate
                sane_prompt = "".join(c if c.isalnum() or c.isspace() else "" for c in user_prompt)
                sane_prompt = sane_prompt.replace(" ", "_")[:50] # Keep first 50 chars
                filename = f"nu_script_{timestamp}_{sane_prompt}.py"
                filepath = os.path.join(self.generated_scripts_path, filename) # Use the class attribute
                with open(filepath, "w") as f:
                    f.write(generated_code)
                print(f"Generated script saved to: {filepath}")
            except Exception as e:
                print(f"Error saving script: {e}")

        if execute_script:
            print("\n--- Attempting to execute generated code ---")
            try:
                # Prepare a global context for exec, similar to how a script would run
                exec_globals = {
                    "__name__": "__main__", # Mimic script execution context
                    # Potentially pass NetUnicorn credentials if needed for some obscure reason,
                    # but the script should ideally get them from the RAG system or define them directly.
                    # "NETUNICORN_ENDPOINT": self.netunicorn_endpoint,
                    # "NETUNICORN_LOGIN": self.netunicorn_login,
                    # "NETUNICORN_PASSWORD": self.netunicorn_password,
                }
                exec(generated_code, exec_globals)
                print("--- Execution finished ---")
            except Exception as e:
                print(f"Error executing generated code: {e}")
                import traceback
                traceback.print_exc()
        
        return generated_code

    # Log retrieved chunks that model finds most relevant
    def log_retrieved_chunks(self, user_prompt: str, k: int = 3) -> str:
        retriever = self.vector_store.as_retriever()
        retrieved_docs = retriever.invoke(user_prompt)
        log = [f"Retrieved Context Chunks for: \"{user_prompt}\"\n"]

        for i, doc in enumerate(retrieved_docs[:k]):
            source = doc.metadata.get('source', 'unknown')
            content = doc.page_content.strip()[:1000] # Limit length for brevity
            log.append(f"Chunk {i+1} (source: {source}): \n")
            log.append("```\n" + content + "\n```\n")

        return "\n".join(log)


# Main block for direct testing (remove or keep for utility)
if __name__ == '__main__':
    try:
        # This main block is for testing the RAG class itself.
        # When running examples/generate_netunicorn_script.py, that script's main is used.
        # Ensure .env is in the project root (NL4NetUnicorn/.env)
        print("Testing NetUnicornRAG directly from netunicorn_rag.py...")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Attempting to load .env from: {os.path.join(os.path.dirname(__file__), '..', '..', '.env')}")
        
        rag_system = NetUnicornRAG() # docs_path will be relative to project root due to updated __init__
        
        test_prompt = "Create a NetUnicorn script that connects to the server, selects one available node, and runs a sleep task for 10 seconds."
        
        print("\n--- Logging Retrieved Chunks ---")
        print(rag_system.log_retrieved_chunks(test_prompt))
        print("-----------------------------")
        
        print(f"\nTesting RAG system with prompt: \"{test_prompt}\"")
        code = rag_system.generate_code(test_prompt, save_script=True, execute_script=False) # Test save, no exec
        
        print("\n--- Generated Code ---")
        print(code)
        print("----------------------")

    except FileNotFoundError as e:
        print(f"Error during direct testing: {e}. Ensure .env file is in project root and docs exist.")
    except ValueError as e:
        print(f"Configuration Error during direct testing: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during direct testing: {e}")
        import traceback
        traceback.print_exc() 