import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import json
from dotenv import load_dotenv

class NetUnicornRAG:
    def __init__(self):
        """Initialize the RAG system for netunicorn code generation."""
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
        
        self.llm = ChatOpenAI(
            model_name="gpt-4-turbo-preview",
            temperature=0,
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
                
        # Create vector store
        self._create_vector_store(texts)
        
    def _create_vector_store(self, texts: List[str]):
        """Create a vector store from the provided texts."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        documents = text_splitter.create_documents(texts)
        self.vector_store = FAISS.from_documents(documents, self.embeddings)
        
    def generate_code(self, prompt: str) -> str:
        """Generate netunicorn code based on the natural language prompt."""
        # Create the prompt template
        template = """
        You are a netunicorn expert. Based on the following documentation and examples:
        {context}
        
        Generate a Python script that uses netunicorn to accomplish the following task:
        {question}
        
        The code should:
        1. Use the netunicorn API correctly with the provided credentials:
           - Endpoint: {endpoint}
           - Login: {login}
           - Password: {password}
        2. Include proper error handling
        3. Follow best practices
        4. Include necessary imports
        5. Be well-documented
        6. Use appropriate netunicorn tasks and pipelines
        7. Handle experiment lifecycle (preparation, execution, results)
        8. Include proper logging and status checks
        
        Return only the Python code, no explanations.
        """
        
        prompt_template = PromptTemplate(
            template=template,
            input_variables=["context", "question", "endpoint", "login", "password"]
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
        
        # Generate the code
        result = qa_chain.invoke({
            "query": prompt,
            "endpoint": self.endpoint,
            "login": self.login,
            "password": self.password
        })
        return result["result"]
        
    def add_documentation(self, text: str):
        """Add new documentation to the vector store."""
        if self.vector_store is None:
            self._create_vector_store([text])
        else:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            documents = text_splitter.create_documents([text])
            self.vector_store.add_documents(documents) 