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
spinner = Halo(text="Loading", spinner="dots")

DATA_DIR = "./data"
files = os.listdir(DATA_DIR)
terminal_menu = TerminalMenu(files)
selected_index = terminal_menu.show()
pdf_file = DATA_DIR + "/" + files[selected_index]
print(f"[{pdf_file}] selected.")

print("Available tools:")
pp(pdf_reader.tool_map)

chat_agent = ChatOllama(
    base_url=OLLAMA_SERVER_URL,
    model="qwen3:14b",
    reasoning=True,
).bind_tools(pdf_reader.tools)

spinner.start('initializing vector store...')
asyncio.run(pdf_reader.db_init(pdf_file))
spinner.stop()
print("Vector store initialized.")

messages = [
    SystemMessage(content='\n'.join([
        "A pdf file is provided. You can use the tools provided to read and query the PDF file.",
        "user's locale is ko-KR, so you should answer in Korean.",
    ])),
    HumanMessage(content="what is the main topic of the PDF?"),
]


def main() -> None:
    spinner.start('asking AI...')
    ai_msg = chat_agent.invoke(messages)
    spinner.stop()

    print("=" * 25, '\nAI Response:\n')
    pp(ai_msg.tool_calls)

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


if __name__ == "__main__":
    main()

