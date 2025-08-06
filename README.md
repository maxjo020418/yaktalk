# yaktalk

1. user query + pdf file
2. parse & embed pdf file -> in mem. DB
3. summarize pdf -> query / comapare to knowledge-base
4. highlight appropriate parts based on prev. output

Launch from `main.py`

### `.env` setup
```bash
# "openai" | "ollama"
# any service that supports the openai's v1
LLM_SERVICE="openai"

# when using Ollama
OLLAMA_SERVER_URL="address-here"
OLLAMA_SERVER_PORT="11434"

# when using OpenAI API
OPEN_API_KEY="sk-proj-..."
```