from langchain_core.globals import set_debug
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.vectorstores import InMemoryVectorStore

from langgraph.graph import StateGraph, START, END, MessageGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from utils.get_env import DATA_DIR
from utils.get_model import get_model
from call_functions import pdf_reader

from pathlib import Path
from typing_extensions import TypedDict
from typing import Annotated, List, Sequence, cast

import os
from simple_term_menu import TerminalMenu

set_debug(True)
memory = InMemorySaver()

def get_pdf_file() -> str:
    """Get the PDF file to be used."""
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
    if not files:
        raise FileNotFoundError("No PDF files found in the data directory.")
    terminal_menu = TerminalMenu(files)
    selected_index = terminal_menu.show()
    if selected_index is None:
        raise ValueError("No file selected")
    if isinstance(selected_index, int):
        return os.path.join(DATA_DIR, files[selected_index])
    else:
        raise ValueError("Invalid selection")


class MainState(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[Sequence[BaseMessage], add_messages]


graph_builder = StateGraph(MainState)

llm = get_model(
    tools=pdf_reader.tools,
    model="qwen3:14b",  # or any other model you want to use
    num_ctx=4096,  # depends on vram
)

pdf_search_tool = ToolNode(
    name="pdf_reader",
    tools=pdf_reader.tools,
)

def chatbot(state: MainState) -> MainState:
    return {
        "messages": [
            llm.invoke(state["messages"], config={"configurable": {"thread_id": "1"}})
        ]
    }

def pdf_search(state: MainState) -> MainState:
    if not pdf_reader.is_vector_store_initialized():
        print("Initializing vector store...", end="")
        pdf_reader.initialize_vector_store(
            pdf_file_path=get_pdf_file(),
            embed_model="qwen3:14b",
            chunk_size=512,
            chunk_overlap=20
        )
        print(" done.")

    last_message = state["messages"][-1]
    # Cast to AIMessage to access tool_calls
    ai_message = cast(AIMessage, last_message)
    if hasattr(ai_message, 'tool_calls') and ai_message.tool_calls:
        tool_args: list[dict] = [
            {
                **call,  # copy all top-level fields: name, id, type…
                "args": call["args"]  # use existing args without adding vector_store
            }
            for call in ai_message.tool_calls
        ]
    else:
        raise ValueError("No tool calls found in the last message")

    tool_response = pdf_search_tool.invoke(tool_args)
    if tool_response is not None:
        # pull out the actual ToolMessage(s) from the returned dict
        msgs = tool_response.get("messages", [])
        if not msgs:
            raise ValueError("Tool returned no messages")
        tool_msg = msgs[-1]

        # now pass SystemMessage + ToolMessage into the LLM
        res = llm.invoke(
            [
                SystemMessage("Use the tool output to answer the user's question."),
                tool_msg
            ],
            config={"configurable": {"thread_id": "1"}}
        )
        return {
            "messages": [res]
        }
    else:
        raise ValueError("Tool response is None. Please check the tool invocation.")

def is_fcall(state: MainState) -> str:
    last_message = state["messages"][-1]
    # Cast to AIMessage to access tool_calls
    ai_message = cast(AIMessage, last_message)
    if hasattr(ai_message, 'tool_calls') and ai_message.tool_calls:
        return "pdf_search"
    else:
        return END

def compile_graph() -> CompiledStateGraph:
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("pdf_search", pdf_search)

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges(
        "chatbot", is_fcall,
        path_map=["pdf_search", END]
    )
    graph_builder.add_edge("pdf_search", END)

    return graph_builder.compile(checkpointer=memory)

############################################################

if __name__ == "__main__":

    append_system_msg = True

    graph: CompiledStateGraph = compile_graph()

    Path("diagram.png").write_bytes(graph.get_graph().draw_mermaid_png())

    def stream_graph_updates(user_input: str, append_system_msg: bool = False):
        # use the already-defined system prompt when append_system_msg=True
        if append_system_msg:
            msgs = [
                SystemMessage(
                    "You can use the tools provided to read and query a PDF file."
                    "You can also answer the user's question directly if you can."
                    "once you prompt the tool, the pdf file would be read."
                ),
                HumanMessage(user_input)
            ]
        else:
            msgs = [HumanMessage(user_input)]

        initial = MainState(
            messages=msgs
        )

        # supply thread_id ONLY for main branch, not the pdf_search branch
        for event in graph.stream(
            initial,
            config={"configurable": {"thread_id": "1"}}
        ):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input, append_system_msg=append_system_msg)
        append_system_msg = False