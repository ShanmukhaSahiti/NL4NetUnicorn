import os
import logging
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NetUnicornRAG:
    def __init__(self, model_name: str = "gpt-4-turbo-preview", temperature: float = 0):
        """Initialize the RAG system for netunicorn code generation.
        
        Args:
            model_name (str): The OpenAI model to use
            temperature (float): The temperature for model generation
        """
        # Load environment variables
        load_dotenv()
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
        # Get netunicorn credentials
        self.endpoint = os.getenv("NETUNICORN_ENDPOINT")
        self.login = os.getenv("NETUNICORN_LOGIN")
        self.password = os.getenv("NETUNICORN_PASSWORD")
        
        if not all([self.endpoint, self.login, self.password]):
            raise ValueError("Netunicorn credentials not set in environment variables")
        
        logger.info(f"Initializing RAG system with model: {model_name}")
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            api_key=openai_api_key
        )
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Initialize vector store
        self.vector_store = None
        
        # Load documentation and examples
        self._load_documentation()
        
    def _load_documentation(self):
        """Load and process netunicorn documentation and examples."""
        try:
            # Load documentation from JSON files
            docs_dir = "nl4netunicorn-rag/data"
            
            # Load documentation
            with open(os.path.join(docs_dir, "documentation.json"), "r") as f:
                docs = json.load(f)
                
            # Load examples
            with open(os.path.join(docs_dir, "examples.json"), "r") as f:
                examples = json.load(f)
                
            # Process documentation into chunks
            texts = []
            
            # Process documentation
            for doc in docs:
                content = doc['content']
                
                # Add title
                if content.get('title'):
                    texts.append(f"Title: {content['title']}")
                    
                # Add text content
                for section in content.get('text_content', []):
                    texts.append(f"{section['type'].upper()}: {section['content']}")
                    
                # Add code blocks
                for code in content.get('code_blocks', []):
                    texts.append(f"Code Example ({code['language']}):\n{code['content']}")
                    
            # Process examples
            for example in examples:
                content = example['content']
                
                # Add imports
                if content.get('imports'):
                    texts.append("Required Imports:")
                    texts.extend(content['imports'])
                    
                # Add functions
                if content.get('functions'):
                    texts.append("Available Functions:")
                    for func in content['functions']:
                        texts.append(f"def {func['name']}({func['parameters']})")
                        
                # Add full code
                if content.get('content'):
                    texts.append(f"Full Example Code:\n{content['content']}")
                    
            logger.info(f"Processed {len(texts)} documentation chunks")
            
            # Create vector store
            self._create_vector_store(texts)
            
        except Exception as e:
            logger.error(f"Error loading documentation: {str(e)}")
            raise
            
    def _create_vector_store(self, texts: List[str]):
        """Create a vector store from the provided texts."""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            documents = text_splitter.create_documents(texts)
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            logger.info(f"Created vector store with {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise
        
    def generate_code(self, prompt: str) -> str:
        """Generate netunicorn code based on the natural language prompt.
        
        Args:
            prompt (str): The natural language prompt describing the desired code
            
        Returns:
            str: The generated Python code
            
        Raises:
            ValueError: If the prompt is empty or invalid
            RuntimeError: If there's an error during code generation
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
            
        try:
            # Get credentials from environment variables
            endpoint = os.getenv("NETUNICORN_ENDPOINT", "https://pinot.cs.ucsb.edu/netunicorn")
            login = os.getenv("NETUNICORN_LOGIN", "293nmay25")
            password = os.getenv("NETUNICORN_PASSWORD", "4Ij9Du65jrqj")
            
            # Inject credentials into the prompt
            credentials_info = f"\nUse the following netunicorn API credentials in your code:\n- Endpoint: {endpoint}\n- Login: {login}\n- Password: {password}\n"
            # The user's prompt is the query, credentials are appended in the template
            user_query = f"{prompt}\n{credentials_info}"

            # Create the enhanced prompt template
            template = """
            You are a netunicorn expert. Based on the following documentation and examples:
            {context}
            
            Generate a Python script that uses netunicorn to accomplish the following task:
            {query}
            
            The code should:
            1. Use the netunicorn API correctly with the provided credentials
            2. Include proper error handling and try-except blocks
            3. Follow Python best practices and PEP 8 style guide
            4. Include all necessary imports at the top
            5. Include detailed docstrings and comments
            6. Use appropriate netunicorn tasks and pipelines
            7. Handle experiment lifecycle (preparation, execution, results)
            8. Include proper logging and status checks
            9. Validate inputs and outputs
            10. Include type hints for function parameters and return values
            
            The code should be production-ready and follow these specific guidelines:
            - Use async/await for API calls
            - Implement proper resource cleanup
            - Include timeout handling
            - Add retry logic for failed operations
            - Use environment variables for configuration
            - Include proper error messages and logging
            
            Return only the Python code, no explanations.
            """
            
            prompt_template = PromptTemplate(
                template=template,
                input_variables=["context", "query"]
            )
            
            # Create the QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(
                    search_kwargs={"k": 5}  # Retrieve top 5 most relevant chunks
                ),
                chain_type_kwargs={"prompt": prompt_template}
            )
            
            logger.info("Generating code for prompt")
            # Generate the code
            result = qa_chain({"query": user_query})
            
            generated_code = result["result"]
            logger.info("Code generation completed successfully")
            return generated_code
            
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            raise RuntimeError(f"Failed to generate code: {str(e)}")
        
    def add_documentation(self, text: str):
        """Add new documentation to the vector store.
        
        Args:
            text (str): The documentation text to add
            
        Raises:
            ValueError: If the text is empty
        """
        if not text or not text.strip():
            raise ValueError("Documentation text cannot be empty")
            
        try:
            if self.vector_store is None:
                self._create_vector_store([text])
            else:
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                documents = text_splitter.create_documents([text])
                self.vector_store.add_documents(documents)
                logger.info(f"Added {len(documents)} new documentation chunks")
        except Exception as e:
            logger.error(f"Error adding documentation: {str(e)}")
            raise 