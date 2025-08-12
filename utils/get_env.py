import os
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

LLM_SERVICE = os.getenv("LLM_SERVICE")
LLM_MODEL = os.getenv("LLM_MODEL")
OPEN_API_KEY = SecretStr("NO_KEY")

if osu := os.getenv("OLLAMA_SERVER_URL"):
    OLLAMA_SERVER_URL = osu
    OLLAMA_SERVER_PORT = os.getenv("OLLAMA_SERVER_PORT") or "11434"
else:
    raise ValueError("OLLAMA_SERVER_URL must be set up for Ollama embeddings (and optional LLM svc)")

assert LLM_MODEL, "model must be set up for services"

match LLM_SERVICE:
    case "ollama":
        assert OLLAMA_SERVER_URL and OLLAMA_SERVER_PORT, \
            "OLLAMA_SERVER_URL and OLLAMA_SERVER_PORT must be set up"
        print(f'Using Ollama server: {OLLAMA_SERVER_URL}')
    case "openai":
        assert os.getenv("OPEN_API_KEY"), \
            "OPEN_API_KEY must be set up for OpenAI service"
        if res := os.getenv("OPEN_API_KEY"):
            OPEN_API_KEY: SecretStr = SecretStr(res)
        else:
            print("OpenAI API key not found.")
            OPEN_API_KEY = SecretStr('')
        print(f"Using OpenAI API with key: {OPEN_API_KEY.get_secret_value()[:10]}...")
    case _:
        raise ValueError("LLM_SERVICE must be set to 'openai' or 'ollama'")

# Law API configuration
OPEN_LAW_GO_ID = os.getenv("OPEN_LAW_GO_ID", "test")

DATA_DIR="./data"