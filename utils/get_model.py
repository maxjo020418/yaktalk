from langchain_core.runnables import Runnable
from langchain_core.utils.function_calling import convert_to_openai_function

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from utils.get_env import LLM_SERVICE, OLLAMA_SERVER_URL, LLM_MODEL, OPEN_API_KEY
from typing import Sequence

def get_model(tools: Sequence, 
              model: str | None = None,
              num_ctx: int = 4096,
              reasoning: bool = True
              ) -> Runnable:
    """
    Docstring for get_model
    
    :param tools: tool_map 반환 하면 됨.
    :type tools: Sequence
    :param model: supported model for respective services, default is LLM_MODEL from env
    :type model: str | None
    :param num_ctx: default 4096, depends on vram
    :type num_ctx: int
    :param reasoning: default True
    :type reasoning: bool
    :return: runnable object for the langchain chat agent
    :rtype: Runnable[Any, Any]
    """
    
    model = model or LLM_MODEL  # model override if provided
    assert model, "model must be set up for services"

    # convert tools to OpenAI function calls if using OpenAI service
    # if LLM_SERVICE == "openai" or model.startswith("gpt-oss:"):
    #     tools = [convert_to_openai_function(tool) for tool in tools]

    match LLM_SERVICE:
        case "ollama":
            print(f"creating chat agent {model} with Ollama.")
            return ChatOllama(
                base_url=OLLAMA_SERVER_URL,
                model=model,
                reasoning=reasoning,  # model needs to support reasoning
                num_ctx=num_ctx,  # depends on vram
            ).bind_tools(tools)

        case "openai":
            print(f"creating chat agent {model} with OpenAI.")
            return ChatOpenAI(
                    model=model, 
                    api_key=OPEN_API_KEY,
            ).bind_tools(tools)
        
        case _:
            raise ValueError(f"Unsupported LLM service: {LLM_SERVICE}")
