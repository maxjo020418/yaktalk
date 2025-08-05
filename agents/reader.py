# Langchain
from langchain_ollama import ChatOllama
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage

# system/default
import os
from pprint import pp
import asyncio

# installed
from halo import Halo
from simple_term_menu import TerminalMenu

# internal
from utils.get_env import OLLAMA_SERVER_URL
from call_functions import pdf_reader


#       === SETUP ===
DATA_DIR = "./data"
files = os.listdir(DATA_DIR)
terminal_menu = TerminalMenu(files)
selected_index = terminal_menu.show()
pdf_file = DATA_DIR + "/" + files[selected_index]
print(f"{pdf_file} selected.")

spinner = Halo(text="Loading", spinner="dots")

print("Available tools:")
pp(pdf_reader.tool_map)

chat_agent = ChatOllama(
    base_url=OLLAMA_SERVER_URL,
    model="qwen3:14b",
    reasoning=True,
).bind_tools(pdf_reader.tools)

asyncio.run(pdf_reader.db_init(pdf_file))
print("Vector store initialized.")

messages = [
    SystemMessage(content="A pdf file is provided. You can use the tools to read and query the PDF file."),
    HumanMessage(content="what is the main topic of the PDF?"),
]


def main() -> None:
    spinner.start()
    ai_msg = chat_agent.invoke(messages)
    spinner.stop()

    print("=" * 10)
    pp(ai_msg.tool_calls)

    for tool_call in ai_msg.tool_calls:
        selected_tool = pdf_reader.tool_map[tool_call["name"].lower()]
        tool_output = selected_tool.invoke(tool_call["args"])
        messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))

    spinner.start()
    ai_msg2 = chat_agent.invoke(messages)
    spinner.stop()

    pp(ai_msg2.content)


if __name__ == "__main__":
    main()

