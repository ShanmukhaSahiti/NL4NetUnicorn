import os
import json
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

class NetUnicornRAG:
    def __init__(self, docs_path="nl4netunicorn_llm/data/netunicorn_docs.json"):
        load_dotenv(dotenv_path="nl4netunicorn_llm/.env")

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")

        self.netunicorn_endpoint = os.getenv("NETUNICORN_ENDPOINT")
        self.netunicorn_login = os.getenv("NETUNICORN_LOGIN")
        self.netunicorn_password = os.getenv("NETUNICORN_PASSWORD")
        if not all([self.netunicorn_endpoint, self.netunicorn_login, self.netunicorn_password]):
            raise ValueError("NetUnicorn credentials not found in environment variables.")

        self.llm = ChatOpenAI(openai_api_key=self.openai_api_key, model_name="gpt-3.5-turbo", temperature=0)
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)

        self.docs = self._load_documents(docs_path)
        self.vector_store = self._create_vector_store(self.docs)
        self.rag_chain = self._setup_rag_chain()

    def _load_documents(self, path: str) -> list[Document]:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Doc file not found: {path}")
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
        Your task is to generate a complete, runnable NetUnicorn Python script based on the user\'s request and relevant NetUnicorn documentation context provided.
        The script should interact with a NetUnicorn server using the provided credentials.

        Context: {context}
        User\'s request: {input}

        Please generate the Python script adhering to the following guidelines:
        1.  **Complete and Runnable Script**: Ensure the script includes all necessary imports (primarily from `netunicorn.client.remote.RemoteClient`, `netunicorn.base.pipeline.Pipeline`, `netunicorn.library.tasks.*`, and `netunicorn.base.nodes.NodePool` if filtering by specific node properties).
        2.  **Credentials**: Use these NetUnicorn credentials for `RemoteClient`:
            Endpoint: `{endpoint}`
            Login: `{login}`
            Password: `{password}`
        3.  **Client Initialization**: Create a `RemoteClient` instance with the provided credentials.
        4.  **Pipeline Creation**:
            *   Instantiate `Pipeline()`.
            *   Add tasks to the pipeline using the `.then()` method. For example: `pipeline.then(SleepTask(10))`.
            *   If the user requests a specific task, use that task. Otherwise, default to `SleepTask(5)`.
        5.  **Node Selection**:
            *   Get all available nodes using `client.get_nodes()`.
            *   Filter nodes if specified in the request. If not, select one available node using `nodes.take(1)`. A more robust selection is to filter for a known available node name if possible, e.g., `nodes.filter(lambda node: node.name == \'snl-server-5\').take(1)`. Ensure `working_nodes` is a list-like structure (e.g., the result of `.take(N)`).
        6.  **Experiment Naming**:
            *   Use a unique string for the experiment name, for example, `experiment_name = "nl4netunicorn_experiment"`.
            *   Before preparing the experiment, attempt to delete any pre-existing experiment with the same name:
                ```python
                try:
                    client.delete_experiment(experiment_name)
                except Exception as e:
                    print(f"Error deleting experiment {{experiment_name}}: {{e}} (possibly non-existent, safe to ignore)")
                ```
        7.  **Experiment Lifecycle & Results**:
            *   Prepare the experiment: `client.prepare_experiment(pipeline, working_nodes, experiment_name)`
            *   Start the experiment execution: `client.start_execution(experiment_name)`
            *   Wait for the experiment to complete: `client.wait_for_experiment(experiment_name)`
            *   Retrieve and print results: 
                ```python
                results = client.get_experiment_status(experiment_name).execution_result
                print(f"Experiment results: {{results}}")
                ```
        8.  **Output Format**: Generate only the Python code block. Do not include any explanatory text before or after the code block.
        9.  **Error Handling**: Include basic error handling for operations like deleting an experiment.
        10. **Imports**: Ensure all imports are at the top of the script.
        ''')
        prompt = ChatPromptTemplate.from_messages([("system", system_prompt)])
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        return create_retrieval_chain(retriever, question_answer_chain)

    def generate_code(self, user_prompt: str) -> str:
        if not user_prompt:
            raise ValueError("User prompt cannot be empty.")
        response = self.rag_chain.invoke({
            "input": user_prompt, 
            "endpoint": self.netunicorn_endpoint,
            "login": self.netunicorn_login,
            "password": self.netunicorn_password
        })
        generated_code = response.get("answer", "")
        if generated_code.startswith("```python"):
            generated_code = generated_code[len("```python"):].strip()
        if generated_code.endswith("```"):
            generated_code = generated_code[:-len("```")].strip()
        return generated_code

# Main block for direct testing (remove or keep for utility)
if __name__ == '__main__':
    try:
        rag_system = NetUnicornRAG()
        test_prompt = "Create a NetUnicorn script that connects to the server, selects one available node, and runs a sleep task for 10 seconds."
        print(f"Testing RAG system with prompt: \"{test_prompt}\"")
        code = rag_system.generate_code(test_prompt)
        print("--- Generated Code ---")
        print(code)
        print("----------------------")
    except Exception as e:
        print(f"An error occurred during direct testing: {e}") 