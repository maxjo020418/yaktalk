# Langchain
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

# system/default
import os
from pprint import pp

# installed
from halo import Halo
from simple_term_menu import TerminalMenu
from langchain_community.document_loaders import PyMuPDFLoader

# internal
from utils.get_env import OLLAMA_SERVER_URL
from call_functions import test

#       === SETUP ===
DATA_DIR = "./data"

files = os.listdir(DATA_DIR)
terminal_menu = TerminalMenu(files)
selected_index = terminal_menu.show()
pdf_file = DATA_DIR + "/" + files[selected_index]

print(f"{pdf_file} selected.")
loader = PyMuPDFLoader(pdf_file)

spinner = Halo(text='Loading', spinner='dots')

print("Available tools:")
pp(test.tool_map)

chat_agent = ChatOllama(
    base_url=OLLAMA_SERVER_URL,
    model='qwen3:14b',
    reasoning=True,
).bind_tools(test.tools)

##############################################################

messages = [
    (
        "system",
        "You are a helpful assistant that can also call tools.",
    ),
    ("human", "what is the addition and multiplication of 14 and 987 ?"),
]

spinner.start()
ai_msg = chat_agent.invoke(messages)
spinner.stop()

# pp(ai_msg.additional_kwargs)
# pp(ai_msg)

print("="*10)
pp(ai_msg.tool_calls)

for tool_call in ai_msg.tool_calls:
    selected_tool = test.tool_map[tool_call["name"].lower()]
    tool_output = selected_tool.invoke(tool_call["args"])
    messages.append(ToolMessage(tool_output, tool_call_id=tool_call["id"]))

spinner.start()
ai_msg = chat_agent.invoke(messages)
spinner.stop()

pp(ai_msg.content)