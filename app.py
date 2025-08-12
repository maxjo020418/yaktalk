import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from typing_extensions import TypedDict
from typing import Annotated, Sequence, cast

import chainlit as cl

from langchain_core.globals import set_debug
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from utils.get_model import get_model
from call_functions import pdf_reader, law_api

# Enable debug mode for development
set_debug(True)

# Global memory for the graph
memory = InMemorySaver()


class MainState(TypedDict):
    """메인 상태 정의"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    pdf_initialized: bool
    law_initialized: bool


class ChainlitLawChatbot:
    """Chainlit용 법률 챗봇 클래스"""
    
    def __init__(self):
        self.all_tools = pdf_reader.tools + law_api.tools
        self.llm = get_model(
            tools=self.all_tools,
            model="qwen3:14b",
            num_ctx=4096,
        )
        self.graph = self._build_graph()
        self.current_pdf_file: Optional[str] = None
    
    def _build_graph(self) -> CompiledStateGraph:
        """LangGraph 빌드"""
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
    
    async def initialize_pdf(self, pdf_file_path: str) -> str:
        """PDF 파일 초기화"""
        try:
            print(f"✅ PDF 초기화 중: {os.path.basename(pdf_file_path)}")
            
            pdf_reader.initialize_chromadb(
                pdf_file_path=pdf_file_path,
                chunk_size=1024,
                chunk_overlap=100
            )
            
            self.current_pdf_file = pdf_file_path
            return f"PDF 문서 '{os.path.basename(pdf_file_path)}'가 성공적으로 로드되었습니다."
            
        except Exception as e:
            error_msg = f"PDF 초기화 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def _initialize_system(self, state: MainState) -> MainState:
        """시스템 초기화"""
        messages = []
        
        # PDF 초기화 상태 확인
        if not state.get("pdf_initialized", False) and self.current_pdf_file:
            if pdf_reader.is_chromadb_initialized():
                messages.append(SystemMessage(
                    f"PDF document '{os.path.basename(self.current_pdf_file)}' is ready for analysis."
                ))
        
        # 법령 DB 초기화 (자동)
        if not state.get("law_initialized", False):
            messages.append(SystemMessage("Legal database has been initialized."))
        
        return {
            "messages": messages,
            "pdf_initialized": bool(self.current_pdf_file and pdf_reader.is_chromadb_initialized()),
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
        
        response = self.llm.invoke(messages, config={"configurable": {"thread_id": "chainlit_session"}})

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
    
    async def process_message(self, user_input: str, pdf_initialized: bool = False, law_initialized: bool = False) -> str:
        """사용자 메시지 처리"""
        initial_state = MainState(
            messages=[HumanMessage(user_input)],
            pdf_initialized=pdf_initialized,
            law_initialized=law_initialized
        )
        
        # 그래프 실행 및 응답 수집
        responses = []
        async for event in self.graph.astream(
            initial_state,
            config={"configurable": {"thread_id": "chainlit_session"}}
        ):
            for value in event.values():
                if "messages" in value and value["messages"]:
                    last_msg = value["messages"][-1]
                    if hasattr(last_msg, 'content') and last_msg.content and isinstance(last_msg, AIMessage):
                        # 도구 호출이 아닌 실제 응답만 수집
                        if not (hasattr(last_msg, 'tool_calls') and last_msg.tool_calls):
                            responses.append(last_msg.content)
        
        # 최종 응답 반환
        return responses[-1] if responses else "죄송합니다. 응답을 생성할 수 없습니다."


# 전역 챗봇 인스턴스
chatbot = ChainlitLawChatbot()


@cl.on_chat_start
async def on_chat_start():
    """채팅 시작 시 실행"""
    await cl.Message(
        content="⚖️ **법률 AI 어시스턴트**에 오신 것을 환영합니다!\n\n"
                "📋 **사용 방법:**\n"
                "1. 📄 PDF 문서를 업로드하여 분석을 시작하세요\n"
                "2. 💬 파일 업로드와 동시에 질문을 보내면 자동으로 처리됩니다\n"
                "3. 📋 PDF 내용에 대해 질문하시면 관련 법령에 근거한 답변을 제공합니다\n"
                "4. 🔍 모든 답변은 구체적인 법령 조항을 근거로 작성됩니다\n\n"
                "**📁 PDF를 업로드하여 시작하세요!**\n"
                "💡 **팁**: 파일 업로드 시 메시지를 함께 보내면 업로드 완료 후 바로 답변드립니다!",
        elements=[
            cl.Text(name="instructions", content="PDF 업로드 후 문서 분석을 시작할 수 있습니다. 업로드와 함께 질문을 보내면 더 편리합니다.", display="side")
        ]
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """메시지 처리"""
    # 파일 업로드와 메시지를 동시에 처리
    if message.elements:
        # 파일 업로드 처리
        await handle_file_upload(message.elements)
        
        # 업로드와 함께 온 메시지도 처리 (메시지가 있는 경우)
        if message.content and message.content.strip():
            # PDF 초기화가 완료될 때까지 잠시 대기
            import asyncio
            await asyncio.sleep(1)  # PDF 초기화 완료 대기
            
            # 파일 업로드 후 메시지 처리
            if chatbot.current_pdf_file and pdf_reader.is_chromadb_initialized():
                await process_user_query(message.content)
            else:
                await cl.Message(
                    content="📄 PDF 업로드가 완료된 후 질문을 처리하겠습니다."
                ).send()
        return
    
    # 일반 메시지 처리
    if not chatbot.current_pdf_file or not pdf_reader.is_chromadb_initialized():
        await cl.Message(
            content="⚠️ PDF 문서를 먼저 업로드해주세요. 분석할 문서가 없습니다.",
        ).send()
        return
    
    # 사용자 메시지 처리
    await process_user_query(message.content)


async def process_user_query(user_input: str):
    """사용자 쿼리 처리 함수"""
    # 로딩 메시지 표시
    loading_msg = cl.Message(content="🔍 분석 중...")
    await loading_msg.send()
    
    try:
        # 챗봇 처리
        response = await chatbot.process_message(
            user_input, 
            pdf_initialized=True, 
            law_initialized=True
        )
        
        # 로딩 메시지 제거 후 응답 전송
        await loading_msg.remove()
        await cl.Message(content=f"{response}").send()
        
    except Exception as e:
        await loading_msg.remove()
        await cl.Message(
            content=f"❌ 오류가 발생했습니다: {str(e)}\n\n다시 시도해주세요."
        ).send()


async def handle_file_upload(elements: List):
    """파일 업로드 처리"""
    for element in elements:
        # 다양한 파일 요소 타입 체크
        if hasattr(element, 'name') and hasattr(element, 'path'):
            # PDF 파일인지 확인
            if not element.name.lower().endswith('.pdf'):
                await cl.Message(
                    content="❌ PDF 파일만 업로드할 수 있습니다."
                ).send()
                continue
            
            # 파일 처리
            try:
                # 업로드된 파일 경로 사용 (Chainlit이 이미 임시 파일로 저장)
                source_path = Path(element.path)
                
                # 새로운 임시 위치로 복사 (선택사항)
                temp_dir = Path(tempfile.gettempdir()) / "yaktalk_uploads"
                temp_dir.mkdir(exist_ok=True)
                temp_file_path = temp_dir / element.name
                
                print(f"📄 파일 정보: name={element.name}")
                print(f"📁 원본 경로: {source_path}")
                print(f"📁 복사 경로: {temp_file_path}")
                
                # 파일 복사
                shutil.copy2(source_path, temp_file_path)
                
                # 파일 크기 확인
                file_size = temp_file_path.stat().st_size
                print(f"💾 파일 크기: {file_size} bytes")
                
                if file_size == 0:
                    await cl.Message(
                        content="❌ 빈 파일이 업로드되었습니다. 유효한 PDF 파일을 업로드해주세요."
                    ).send()
                    continue
                
                # 로딩 메시지
                loading_msg = cl.Message(content="📚 PDF 문서를 분석 중입니다...")
                await loading_msg.send()
                
                # PDF 초기화
                result = await chatbot.initialize_pdf(str(temp_file_path))
                
                # 결과 메시지
                await loading_msg.remove()
                if "성공적으로" in result:
                    await cl.Message(
                        content=f"✅ **{result}**\n\n이제 문서에 대해 질문하실 수 있습니다! 🎉"
                    ).send()
                    
                    # 파일 정보 표시
                    await cl.Message(
                        content=f"📄 현재 로드된 PDF: {element.name} ({file_size:,} bytes)"
                    ).send()
                else:
                    await cl.Message(
                        content=f"❌ {result}"
                    ).send()
                    
            except Exception as e:
                print(f"❌ 파일 업로드 오류: {str(e)}")
                await cl.Message(
                    content=f"❌ 파일 처리 중 오류가 발생했습니다: {str(e)}"
                ).send()


@cl.on_stop
async def on_stop():
    """채팅 종료 시 정리"""
    # 임시 파일 정리
    temp_dir = Path(tempfile.gettempdir()) / "yaktalk_uploads"
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

