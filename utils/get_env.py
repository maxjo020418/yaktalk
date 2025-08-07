import os
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

LLM_SERVICE = os.getenv("LLM_SERVICE")
LLM_MODEL = os.getenv("LLM_MODEL")
OLLAMA_SERVER_URL = None
OPEN_API_KEY = SecretStr("NO_KEY")

assert LLM_MODEL, "model must be set up for services"

match LLM_SERVICE:
    case "ollama":
        assert os.getenv("OLLAMA_SERVER_URL") and os.getenv("OLLAMA_SERVER_PORT"), \
            "OLLAMA_SERVER_URL and OLLAMA_SERVER_PORT must be set up"
        OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL") + ":" + os.getenv("OLLAMA_SERVER_PORT") # type: ignore
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

DATA_DIR="./data"