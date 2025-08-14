# YAKTALK

YakTalk is a legal assistant that analyzes PDF documents and answers questions citing Korean statutes. It uses LangGraph for orchestration, ChromaDB for vector storage, and Ollama models for local inference.


## Installation

Clone and enter project:
```bash
git clone https://github.com/yourusername/yaktalk.git
cd yaktalk
```

Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Environment variables (`.env`): 
```env
# Required: LLM Service Configuration
LLM_SERVICE=ollama                    # or "openai"  
LLM_MODEL=qwen3:14b                   # model name for chosen service

# Required: Ollama Configuration (if using ollama)
OLLAMA_SERVER_URL=http://localhost:11434
OLLAMA_SERVER_PORT=11434              # optional, defaults to 11434

# Required: OpenAI Configuration (if using openai)
OPEN_API_KEY=your_openai_key_here     # required if LLM_SERVICE=openai

# Required: Korean Law API
OPEN_LAW_GO_ID=your_id_here           # National Law Information Center API key

# Optional: Data Directory
DATA_DIR=./data                       # defaults to "./data"
```

### Getting Korean Law API Key

To obtain the `OPEN_LAW_GO_ID`:
1. Visit the [National Law Information Center Open API](https://open.law.go.kr/)
2. Sign up for an account
3. Apply for API access in the developer section
4. Once approved, copy your API key to the `.env` file

Pull Ollama models:
```bash
# recommended models
ollama pull qwen3:14b
ollama pull nomic-embed-text
```

##  User Interfaces

###  Web Interface (Recommended)
Modern web-based chat interface powered by Chainlit:

#### Option 1: Using shell script
```bash
./start_web.sh
# Access: http://localhost:8000
```

#### Option 2: Direct Chainlit command
```bash
chainlit run app.py --port 8000
# Access: http://localhost:8000
```

The web interface provides:
- Easy PDF file upload via drag & drop
- Real-time document processing
- Interactive chat with legal citations
- Responsive design for mobile and desktop

###  Terminal Interface
Command-line interface:
```bash
python main.py
```

## Key Features

- PDF document ingestion and chunked retrieval
- **PDF text highlighting** - Automatically highlights relevant passages in PDFs
- Korean law lookup (National Law Information Center API)  
- Responses grounded with article citations
- Local embedding for PDFs (privacy, speed)
- Persistent ChromaDB stores for PDFs and laws
- Web-based file upload and chat interface
- Real-time document processing and analysis



## Architecture
![graph diagram](process_diagram.png)

The system architecture follows this flow:
```
User Query
   -> PDF Retrieval (search_pdf_content)
   -> PDF Highlighting (highlight relevant sections)
   -> Law Retrieval (search_law_by_query)
   -> Response (with legal citations and highlighted PDF)
```

### Core Components

1. **PDF Processing** (`call_functions/pdf_reader.py`): load, split, embed, store
2. **PDF Highlighter** (`call_functions/pdf_highlighter.py`): highlight relevant text in PDFs
3. **Law API** (`call_functions/law_api.py`): fetch, normalize, embed statutes  
4. **Chat Orchestrator** (`main.py`): tool routing, state, answer synthesis
5. **Web Interface** (`app.py`): Chainlit-based web UI with file upload

## Prerequisites

- Python 3.8+
- Ollama running with required models
- OPEN_LAW_GO_ID (National Law API credential)


## Usage

###  Web Interface (Recommended)

Start the web application using Chainlit:

#### Method 1: Shell Script
```bash
./start_web.sh
```

#### Method 2: Direct Command
```bash
chainlit run app.py --port 8000
```

#### Method 3: Custom Port
```bash
chainlit run app.py --port 3000  # Use any available port
```

Then:
1. Open http://localhost:8000 in your browser (or your custom port)
2. Upload a PDF file using the chat interface
3. Ask questions about the document
4. Receive responses with legal citations
5. View highlighted sections in the PDF for context

See [WEB_INTERFACE_GUIDE.md](WEB_INTERFACE_GUIDE.md) for detailed usage.

###  Terminal Interface

Start the terminal version:
```bash
python main.py
```

Place PDFs in `data/` directory, then select one at startup. Ask factual or legal questions referencing the loaded PDF.

Exit commands: `quit`, `exit`, `q`, `/exit`.

## Configuration

PDF config (`PDFConfig` in `pdf_reader.py`):
```python
chunk_size = 1024
chunk_overlap = 100
max_content_length = 500
collection_name = "pdf_documents"
search_k = 5
```

Law config (`LawConfig` in `law_api.py`):
```python
chunk_size = 1024
chunk_overlap = 100
max_articles = 50
search_threshold = 2
timeout = 10
```

PDF Highlighter config (`pdf_highlighter.py`):
```python
# Automatically highlights relevant passages
# Normalizes text for robust matching
# Generates highlighted PDF output
```

## How It Works

1. **PDF Processing**: Document upload, page extraction, and chunking
2. **Vector Storage**: Local embedding and ChromaDB persistence
3. **Query Processing**: Retrieve PDF context and relevant statutes
4. **Text Highlighting**: Identify and highlight relevant passages in PDFs
5. **Response Generation**: AI synthesis with legal article citations

## Web Interface Features

- **Drag & Drop Upload**: Easy PDF file upload
- **Real-time Processing**: Instant document analysis
- **Interactive Chat**: Natural language conversation
- **Legal Citations**: Precise statute references
- **PDF Highlighting**: Visual marking of relevant sections
- **Responsive Design**: Works on mobile and desktop

## Troubleshooting

### Common Issues

1. **Web Interface Won't Start**: 
   - Check Ollama server status: `ollama list`
   - Verify Chainlit installation: `pip show chainlit`
   - Try different port: `chainlit run app.py --port 3000`

2. **PDF Upload Fails**: 
   - Verify file size (<50MB)
   - Check PDF format (must be valid PDF)
   - Ensure write permissions in data directory

3. **No Responses**: 
   - Ensure all environment variables are set
   - Check Korean Law API key validity
   - Verify Ollama models are pulled

4. **Port Already in Use**:
   ```bash
   # Find process using port 8000
   lsof -i :8000  # On Mac/Linux
   netstat -ano | findstr :8000  # On Windows
   
   # Use alternative port
   chainlit run app.py --port 8001
   ```

### Performance Tips

- Keep PDFs under 10MB for optimal performance
- Use GPU acceleration if available
- Monitor memory usage with large documents
- Clear ChromaDB cache periodically for better performance
