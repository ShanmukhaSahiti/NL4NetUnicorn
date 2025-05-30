# NL4NetUnicorn

This system uses Retrieval Augmented Generation (RAG) to convert natural language prompts into netUnicorn Python code for data collection tasks.

## Setup

1. Clone directory:
```bash
git clone https://github.com/ShanmukhaSahiti/NL4NetUnicorn.git
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory `(NL4NetUnicorn/)` with your OpenAI API key and netUnicorn login credentials:
```
NETUNICORN_ENDPOINT = your_endpoint_here
NETUNICORN_LOGIN = your_login_here
NETUNICORN_PASSWORD = your_password_here
OPENAI_API_KEY = your_api_key_here
```

## Usage

1. To generate code for a single prompt:
```bash
python nl4netunicorn_llm/src/generate_netunicorn_script.py -p "your prompt here"
```
If you want to save the script to a file, use the `-s` flag. If you want to execute the script, use the `-e` flag.

2. To generate code for one or more prompts and view an evaluation report:
```bash
python evaluate_rag.py -i "file containing one prompt on each line"
```

## Project Structure


- `data/`: Context for RAG system
  - `netunicorn_docs.json`
- `src/`: Source code for the RAG system
  - `netunicorn_rag.py`: Main RAG implementation
  - `generate_netunicorn_script.py`: Generates script for single prompt
- `examples/`: Example usage scripts

## Features

- Converts natural language prompts to netunicorn Python code
- Uses RAG to understand context from documentation and examples
- Supports various data collection tasks
- Generates well-documented, production-ready code