import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any
import os
import re
from urllib.parse import urljoin

class DocumentationLoader:
    def __init__(self):
        self.base_url = "https://netunicorn.github.io/netunicorn/"
        self.docs_url = urljoin(self.base_url, "index.html")
        self.examples_url = urljoin(self.base_url, "examples.html")
        self.library_url = "https://github.com/netunicorn/netunicorn-library"
        
    def _fetch_url(self, url: str) -> str:
        """Fetch content from a URL."""
        response = requests.get(url)
        response.raise_for_status()
        return response.text
        
    def _parse_html(self, html: str, url: str) -> Dict[str, Any]:
        """Extract structured content from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Extract main content
        content = {}
        
        # Get title
        title = soup.find('title')
        content['title'] = title.text if title else ''
        
        # Get main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            # Extract code blocks
            code_blocks = []
            for code in main_content.find_all('pre'):
                code_blocks.append({
                    'language': code.get('class', [''])[0] if code.get('class') else '',
                    'content': code.text.strip()
                })
            content['code_blocks'] = code_blocks
            
            # Extract text content
            text_content = []
            for section in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                text_content.append({
                    'type': section.name,
                    'content': section.text.strip()
                })
            content['text_content'] = text_content
            
            # Extract links
            links = []
            for link in main_content.find_all('a'):
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    links.append({
                        'text': link.text.strip(),
                        'url': full_url
                    })
            content['links'] = links
            
        return content
        
    def _process_code_block(self, code: str) -> Dict[str, Any]:
        """Process a code block to extract relevant information."""
        return {
            'type': 'code',
            'content': code,
            'imports': self._extract_imports(code),
            'functions': self._extract_functions(code)
        }
        
    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements from code."""
        import_pattern = r'^import\s+.*$|^from\s+.*\s+import\s+.*$'
        imports = []
        for line in code.split('\n'):
            if re.match(import_pattern, line.strip()):
                imports.append(line.strip())
        return imports
        
    def _extract_functions(self, code: str) -> List[Dict[str, Any]]:
        """Extract function definitions from code."""
        function_pattern = r'def\s+(\w+)\s*\((.*?)\)\s*:'
        functions = []
        for match in re.finditer(function_pattern, code, re.MULTILINE):
            functions.append({
                'name': match.group(1),
                'parameters': match.group(2)
            })
        return functions
        
    def load_documentation(self) -> List[Dict[str, Any]]:
        """Load and process netunicorn documentation."""
        docs = []
        
        # Load main documentation
        try:
            html = self._fetch_url(self.docs_url)
            content = self._parse_html(html, self.docs_url)
            docs.append({
                'url': self.docs_url,
                'type': 'documentation',
                'content': content
            })
        except Exception as e:
            print(f"Error loading main documentation: {e}")
            
        # Load examples
        try:
            html = self._fetch_url(self.examples_url)
            content = self._parse_html(html, self.examples_url)
            docs.append({
                'url': self.examples_url,
                'type': 'examples',
                'content': content
            })
        except Exception as e:
            print(f"Error loading examples: {e}")
            
        return docs
        
    def load_examples(self) -> List[Dict[str, Any]]:
        """Load example code from the library."""
        examples = []
        
        # Load basic example
        try:
            with open('basic_example.py', 'r') as f:
                code = f.read()
                examples.append({
                    'type': 'example',
                    'name': 'basic_example',
                    'content': self._process_code_block(code)
                })
        except Exception as e:
            print(f"Error loading basic example: {e}")
            
        return examples
        
    def save_documentation(self, output_dir: str):
        """Save processed documentation to files."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save documentation
        docs = self.load_documentation()
        with open(os.path.join(output_dir, "documentation.json"), "w") as f:
            json.dump(docs, f, indent=2)
            
        # Save examples
        examples = self.load_examples()
        with open(os.path.join(output_dir, "examples.json"), "w") as f:
            json.dump(examples, f, indent=2)
            
if __name__ == "__main__":
    loader = DocumentationLoader()
    loader.save_documentation("nl4netunicorn-rag/data") 