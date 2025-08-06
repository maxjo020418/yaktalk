# Langchain
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage

# system/default
import os
from pprint import pp
import asyncio

# installed
from halo import Halo
from simple_term_menu import TerminalMenu

# internal
from utils.get_env import LLM_SERVICE, OLLAMA_SERVER_URL, OPEN_API_KEY, DATA_DIR
from call_functions import pdf_reader

# === SETUP ===
spinner = Halo(text="Loading", spinner="dots")

files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
terminal_menu = TerminalMenu(files)
selected_index = terminal_menu.show()
pdf_file = DATA_DIR + "/" + files[selected_index]
print(f"[{pdf_file}] selected.")

print("Available tools:")
pp(pdf_reader.tool_map)


if LLM_SERVICE == "ollama":
    chat_agent = ChatOllama(
        base_url=OLLAMA_SERVER_URL,
        model="qwen3:14b",
        reasoning=True,  # model needs to support reasoning
        num_ctx=4096,  # depends on vram
    ).bind_tools(pdf_reader.tools)
    print("created chat agent with Ollama.")
elif LLM_SERVICE == "openai":
    chat_agent = ChatOpenAI(
        model="gpt-4o",
        api_key=OPEN_API_KEY,
    ).bind_tools(pdf_reader.tools)
    print("created chat agent with OpenAI.")


# spinner.start('initializing vector store...')
asyncio.run(pdf_reader.db_init(pdf_file))
# spinner.stop()
print("Vector store initialized.")

# === MAIN ===

messages = [
    SystemMessage(content='\n'.join([
        "A pdf file is provided. You can use the tools provided to read and query the PDF file.",
    ])),
    HumanMessage('\n'.join([
        '이 파일에서 위법이 될만한 계약 내용이 있다면 알려줘',
    ])),
]


def main() -> None:
    spinner.start('asking AI...')
    ai_msg = chat_agent.invoke(messages)
    spinner.stop()

    print("=" * 25, '\nAI Response:\n')
    pp(ai_msg.tool_calls)

    messages.append(ai_msg)

    spinner.start('executing tool calls...')
    for tool_call in ai_msg.tool_calls:
        selected_tool = pdf_reader.tool_map[tool_call["name"].lower()]
        tool_output = selected_tool.invoke(tool_call["args"])
        messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))
    spinner.stop()

    spinner.start('asking AI...')
    ai_msg2 = chat_agent.invoke(messages)
    spinner.stop()

    print("=" * 25, '\nAI Response:\n')
    pp(ai_msg2.content)

    print("=" * 25, '\n')
    pp(messages + [SystemMessage("user's locale is ko-KR, so you should answer in Korean.")])


if __name__ == "__main__":
    main()

