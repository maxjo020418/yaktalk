import os
from pathlib import Path
from typing_extensions import TypedDict
from typing import Annotated, Sequence, cast
from simple_term_menu import TerminalMenu

from langchain_core.globals import set_debug
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from utils.get_env import DATA_DIR
from utils.get_model import get_model
from call_functions import pdf_reader, law_api

set_debug(True)
memory = InMemorySaver()


class MainState(TypedDict):
    """메인 상태 정의"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    pdf_initialized: bool
    law_initialized: bool


class LawChatbot:
    """법률 챗봇 메인 클래스"""
    
    def __init__(self):
        self.all_tools = pdf_reader.tools + law_api.tools
        self.llm = get_model(
            tools=self.all_tools,
            model="qwen3:14b",
            num_ctx=4096,
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> CompiledStateGraph:
        """LangGraph 그래프 생성"""
        graph_builder = StateGraph(MainState)
        
        # 노드 추가
        graph_builder.add_node("initialize", self._initialize_system)
        graph_builder.add_node("chatbot", self._chatbot)
        graph_builder.add_node("pdf_tools", self._process_pdf_tool)
        graph_builder.add_node("law_tools", self._process_law_tool)
        
        # 엣지 설정
        graph_builder.add_edge(START, "initialize")
        graph_builder.add_edge("initialize", "chatbot")
        
        # 조건부 라우팅 - chatbot에서 도구로
        graph_builder.add_conditional_edges(
            "chatbot",
            self._route_tools,
            {
                "pdf_tools": "pdf_tools",
                "law_tools": "law_tools", 
                "end": END
            }
        )
        
        # 도구 처리 후 다시 chatbot으로 - 피드백 루프 생성
        graph_builder.add_edge("pdf_tools", "chatbot")
        graph_builder.add_edge("law_tools", "chatbot")
        
        return graph_builder.compile(checkpointer=memory)
    
    def _get_pdf_file(self) -> str:
        """PDF 파일 선택"""
        files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
        if not files:
            raise FileNotFoundError("데이터 디렉토리에 PDF 파일이 없습니다.")
        
        terminal_menu = TerminalMenu(files)
        selected_index = terminal_menu.show()
        
        if selected_index is None:
            raise ValueError("파일이 선택되지 않았습니다.")
        
        # Handle potential tuple return from terminal_menu
        if isinstance(selected_index, tuple):
            selected_index = selected_index[0]
        
        return os.path.join(DATA_DIR, files[selected_index])
    
    def _initialize_system(self, state: MainState) -> MainState:
        """시스템 초기화"""
        messages = []
        
        # PDF 초기화
        if not state.get("pdf_initialized", False):
            if not pdf_reader.is_chromadb_initialized():
                print("\n📚 PDF 문서를 선택해주세요:")
                try:
                    pdf_file = self._get_pdf_file()
                    print(f"✅ PDF 초기화 중: {os.path.basename(pdf_file)}")
                    pdf_reader.initialize_chromadb(
                        pdf_file_path=pdf_file,
                        chunk_size=1024,
                        chunk_overlap=100
                    )
                    messages.append(SystemMessage(f"PDF document '{os.path.basename(pdf_file)}' has been loaded successfully."))
                except Exception as e:
                    messages.append(SystemMessage(f"PDF initialization failed: {str(e)}"))
        
        # 법령 DB 초기화 (자동)
        if not state.get("law_initialized", False):
            print("⚖️ 법령 데이터베이스 초기화 중...")
            messages.append(SystemMessage("Legal database has been initialized."))
        
        return {
            "messages": messages,
            "pdf_initialized": True,
            "law_initialized": True
        }
    
    def _chatbot(self, state: MainState) -> MainState:
        """메인 챗봇 노드"""
        system_prompt = SystemMessage(
            "You are a legal AI assistant specializing in Korean law. "
            "The PDF is the document to be analyzed, and all answers must be based on legal statutes. "
            "Workflow: "
            "1. When user asks about PDF content, use search_pdf_content to examine the document "
            "2. Search for relevant laws using search_law_by_query based on the PDF content "
            "3. Provide answers strictly based on legal statutes with article numbers "
            "IMPORTANT: The PDF is only the subject of analysis, NOT the basis for answers. "
            "All legal judgments and advice must cite specific legal provisions. "
            "ALWAYS respond in Korean language, but follow these English instructions."
        )
        
        # 시스템 프롬프트가 이미 있는지 확인
        messages = list(state["messages"])
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [system_prompt] + messages
        
        response = self.llm.invoke(messages, config={"configurable": {"thread_id": "1"}})

        return MainState(
            messages=list(state["messages"]) + [response],
            pdf_initialized=state["pdf_initialized"],
            law_initialized=state["law_initialized"],
        )

    def _process_pdf_tool(self, state: MainState) -> MainState:
        """PDF 도구 처리"""
        last_message = state["messages"][-1]
        ai_message = cast(AIMessage, last_message)
        
        if not (hasattr(ai_message, 'tool_calls') and ai_message.tool_calls):
            return state
        
        tool_node = ToolNode(tools=pdf_reader.tools)
        tool_response = tool_node.invoke({"messages": [ai_message]})
        
        # 도구 실행 결과를 메시지 리스트에 추가
        new_messages = list(state["messages"]) + tool_response["messages"]
        
        return MainState(
            messages=new_messages,
            pdf_initialized=state["pdf_initialized"],
            law_initialized=state["law_initialized"],
        )
    
    def _process_law_tool(self, state: MainState) -> MainState:
        """법령 도구 처리"""
        last_message = state["messages"][-1]
        ai_message = cast(AIMessage, last_message)
        
        if not (hasattr(ai_message, 'tool_calls') and ai_message.tool_calls):
            return state
        
        tool_node = ToolNode(tools=law_api.tools)
        tool_response = tool_node.invoke({"messages": [ai_message]})
        
        # 도구 실행 결과를 메시지 리스트에 추가
        new_messages = list(state["messages"]) + tool_response["messages"]
        
        return MainState(
            messages=new_messages,
            pdf_initialized=state["pdf_initialized"],
            law_initialized=state["law_initialized"],
        )
    
    def _route_tools(self, state: MainState) -> str:
        """도구 라우팅 결정"""
        last_message = state["messages"][-1]
        ai_message = cast(AIMessage, last_message)
        
        if hasattr(ai_message, 'tool_calls') and ai_message.tool_calls:
            tool_names = [call["name"] for call in ai_message.tool_calls]
            
            # PDF 도구 확인
            if any(name in ["search_pdf_content", "get_pdf_metadata"] for name in tool_names):
                return "pdf_tools"
            
            # 법령 도구 확인
            if any(name in ["search_law_by_query", "load_law_by_id"] for name in tool_names):
                return "law_tools"
        
        return "end"
    
    def run_chat_loop(self):
        """메인 채팅 루프"""
        print("=" * 60)
        print("⚖️  법률 AI 어시스턴트")
        print("=" * 60)
        print("PDF 문서를 분석하여 관련 법령에 근거한 답변을 제공합니다.")
        print("답변은 법령 조항을 근거로 작성됩니다.")
        print("종료하려면 'quit', 'exit', 'q', '/exit'를 입력하세요.")
        print("-" * 60)
        
        # 다이어그램 저장
        Path("langchain_diagram.png").write_bytes(
            self.graph.get_graph().draw_mermaid_png()
        )
        
        # 초기화 플래그
        pdf_initialized = False
        law_initialized = False
        
        while True:
            user_input = input("\n👤 User: ")
            if user_input.lower() in ["quit", "exit", "q", "/exit"]:
                print("\n👋 안녕히 가세요!")
                break
            
            self._stream_graph_updates(user_input, pdf_initialized, law_initialized)
            
            # 초기화 완료 후 플래그 설정
            pdf_initialized = True
            law_initialized = True
    
    def _stream_graph_updates(self, user_input: str, pdf_init: bool = False, law_init: bool = False):
        """그래프 업데이트 스트리밍"""
        initial_state = MainState(
            messages=[HumanMessage(user_input)],
            pdf_initialized=pdf_init,
            law_initialized=law_init
        )
        
        # 그래프 실행
        for event in self.graph.stream(
            initial_state,
            config={"configurable": {"thread_id": "1"}}
        ):
            for value in event.values():
                if "messages" in value and value["messages"]:
                    last_msg = value["messages"][-1]
                    if hasattr(last_msg, 'content') and last_msg.content:
                        print("\n🤖 Assistant:", last_msg.content)


def main():
    """메인 함수"""
    chatbot = LawChatbot()
    chatbot.run_chat_loop()


if __name__ == "__main__":
    main()