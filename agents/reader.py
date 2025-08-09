# Langchain
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage

# system/default
import os
from pprint import pp

# installed
from halo import Halo
from simple_term_menu import TerminalMenu

# internal
from utils.get_env import DATA_DIR
from utils.get_model import get_model
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

chat_agent = get_model(
    tools=pdf_reader.tools,
    num_ctx=4096,  # default: 4096 (depends on vram)
)

pdf_reader.db_init(
    pdf_file,
    embed_model="qwen3:14b",
)
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

    messages.append(ai_msg)

    for tool_call in ai_msg.tool_calls:
        selected_tool = pdf_reader.tool_map[tool_call["name"].lower()]
        tool_output = selected_tool.invoke(tool_call["args"])
        messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))

    # No response from LLM when using SystemMessage as final message (or any other types of message that is...)
    # (only for gpt-oss models)
    # messages.append(SystemMessage("user's locale is ko-KR, answer in Korean....
    messages.append(HumanMessage('\n'.join([
        "user's locale is ko-KR, answer in Korean.",
        "Make sure to make a disclaimer that the AI is not a legal expert and the user should consult a lawyer for legal advice.",
    ])))

    spinner.start('asking AI...')
    ai_msg2 = chat_agent.invoke(messages)
    spinner.stop()

    print('\nAI Response:\n')
    pp(ai_msg2.content)
