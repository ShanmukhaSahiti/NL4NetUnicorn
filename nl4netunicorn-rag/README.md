# NL4NetUnicorn RAG System

This system uses Retrieval Augmented Generation (RAG) to convert natural language prompts into netunicorn Python code for data collection tasks.

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. First, load the documentation:
```bash
python src/load_docs.py
```

2. Run the example code generator:
```bash
python examples/generate_code.py
```

3. To use the system in your own code:
```python
from src.rag_system import NetUnicornRAG

# Initialize the RAG system
rag = NetUnicornRAG(openai_api_key="your_api_key")

# Generate code from a natural language prompt
prompt = """
Create a netunicorn script that collects network performance data from Raspberry Pi nodes.
The script should:
1. Connect to the netunicorn endpoint
2. Select available Raspberry Pi nodes
3. Run a speed test on each node
4. Save the results
"""

generated_code = rag.generate_code(prompt)
```

## Project Structure

- `src/`: Source code for the RAG system
  - `rag_system.py`: Main RAG implementation
  - `load_docs.py`: Documentation loader
- `data/`: Processed documentation and examples
- `examples/`: Example usage scripts

## Features

- Converts natural language prompts to netunicorn Python code
- Uses RAG to understand context from documentation and examples
- Supports various data collection tasks
- Handles error cases and edge conditions
- Generates well-documented, production-ready code

## Contributing

Feel free to submit issues and enhancement requests! 