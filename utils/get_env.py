import os
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

assert os.getenv("LLM_SERVICE") in ["openai", "ollama"], \
    "LLM_SERVICE must be set to 'openai' or 'ollama'"

LLM_SERVICE = os.getenv("LLM_SERVICE")
OLLAMA_SERVER_URL = "NO_URL"
OPEN_API_KEY = SecretStr("NO_KEY")

if os.getenv("LLM_SERVICE") == "ollama":
    assert os.getenv("OLLAMA_SERVER_URL") and os.getenv("OLLAMA_SERVER_PORT"), \
        "OLLAMA_SERVER_URL and OLLAMA_SERVER_PORT must be set up"
    OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL") + ":" + os.getenv("OLLAMA_SERVER_PORT") # type: ignore
    
    print(f'Using Ollama server: {OLLAMA_SERVER_URL}')

elif os.getenv("LLM_SERVICE") == "openai":
    assert os.getenv("OPEN_API_KEY"), \
        "OPEN_API_KEY must be set up for OpenAI service"
    if res := os.getenv("OPEN_API_KEY"):
        OPEN_API_KEY: SecretStr = SecretStr(res)
    else:
        print("OpenAI API key not found.")
        OPEN_API_KEY = SecretStr('')
    
    print(f"Using OpenAI API with key: {OPEN_API_KEY.get_secret_value()[:10]}...")

DATA_DIR="./data"