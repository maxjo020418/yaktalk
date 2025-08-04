import os
from dotenv import load_dotenv

load_dotenv()
assert os.getenv("OLLAMA_SERVER_URL") and os.getenv("OLLAMA_SERVER_PORT"), "Ollama var must be set up"

OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL") + ":" + os.getenv("OLLAMA_SERVER_PORT") # type: ignore
print(f'Ollama server: {OLLAMA_SERVER_URL}')