import os
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from typing_extensions import TypedDict
from typing import Annotated, Sequence, cast

import chainlit as cl

from langchain_core.globals import set_debug
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from utils.get_model import get_model
from call_functions import pdf_reader, law_api, pdf_highlighter

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
    """향상된 Chain of Thought를 가진 Chainlit용 법률 챗봇 클래스"""
    
    def __init__(self):
        self.pdf_tools = pdf_reader.tools + pdf_highlighter.tools
        self.all_tools = self.pdf_tools + law_api.tools
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
        
        # PDF 초기화 상태 확인 - 로직 수정
        if state.get("pdf_initialized", False) and self.current_pdf_file:
            if pdf_reader.is_chromadb_initialized():
                messages.append(SystemMessage(
                    f"IMPORTANT: PDF document '{os.path.basename(self.current_pdf_file)}' is ready for analysis. "
                    f"The document has been processed and is available for search_pdf_content queries."
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
        
        # 동적 시스템 프롬프트 생성
        pdf_status = ""
        if state.get("pdf_initialized", False) and self.current_pdf_file:
            pdf_filename = os.path.basename(self.current_pdf_file)
            pdf_status = f"CURRENT STATUS: PDF document '{pdf_filename}' is loaded and ready for analysis. "
        else:
            pdf_status = "CURRENT STATUS: No PDF document is currently loaded. Ask user to upload a PDF first. "
        
        system_prompt = SystemMessage(
            f"{pdf_status}"
            "You are a legal AI assistant specializing in Korean law. "
            "Workflow: "
            "1. If PDF is loaded: When user asks about PDF content, use search_pdf_content to examine the document "
            "2. Search for relevant laws using search_law_by_query based on the PDF content "
            "3. Provide answers strictly based on legal statutes with article numbers, highlight important or relevant information in the pdf. "
            "4. If no PDF is loaded: Inform user to upload a PDF document first "
            "IMPORTANT: The PDF is only the subject of analysis, NOT the basis for answers. "
            "All legal judgments and advice must cite specific legal provisions via search_law_by_query. (if failed, make it known)"
            "ALWAYS respond in Korean language, but follow these English instructions."
        )
        
        # 시스템 프롬프트가 이미 있는지 확인
        messages = list(state["messages"])
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [system_prompt] + messages
        else:
            # 기존 시스템 메시지를 새로운 것으로 교체 (PDF 상태가 변경될 수 있으므로)
            messages[0] = system_prompt
        
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
        
        tool_node = ToolNode(tools=self.pdf_tools)
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
            if any(name in ["search_pdf_content", "get_pdf_metadata", "highlight_snippet"] for name in tool_names):
                return "pdf_tools"
            
            # 법령 도구 확인
            if any(name in ["search_law_by_query", "load_law_by_id"] for name in tool_names):
                return "law_tools"
        
        return "end"
    
    async def process_message_with_cot(self, user_input: str, pdf_initialized: bool = False, law_initialized: bool = False) -> str:
        """Chain of Thought를 포함한 사용자 메시지 처리"""
        
        initial_state = MainState(
            messages=[HumanMessage(user_input)],
            pdf_initialized=pdf_initialized,
            law_initialized=law_initialized
        )
        
        final_response = ""
        step_count = 1
        
        # 그래프 실행 및 각 단계를 별도의 Step으로 시각화
        async for event in self.graph.astream(
            initial_state,
            config={"configurable": {"thread_id": "chainlit_session"}}
        ):
            for node_name, value in event.items():
                if node_name and "messages" in value and value["messages"]:
                    last_msg = value["messages"][-1]
                    
                    # 시스템 초기화 단계 - 별도 Step
                    if node_name == "initialize":
                        async with cl.Step(name=f"🔧 시스템 시작", type="run") as init_step:
                            init_step.input = "시스템 준비 상태 확인"
                            # await cl.Message(
                            #     content="✅ PDF 문서와 법령 데이터베이스 연결 상태를 확인합니다.",
                            #     parent_id=init_step.id
                            # ).send()
                            init_step.output = "시스템 준비 완료"
                        step_count += 1
                    
                    # 챗봇 추론 단계 - 별도 Step
                    elif node_name == "chatbot":
                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                            # AI 추론 및 도구 선택 단계
                            async with cl.Step(name=f"🤖 추론 및 도구 선택", type="run") as reasoning_step:
                                reasoning_step.input = user_input
                                
                                tool_names = [call["name"] for call in last_msg.tool_calls]
                                # await cl.Message(
                                #     content=f"💭 **사용자 질문 분석**: {user_input}\n\n"
                                #            f"🎯 **AI 판단**: 이 질문에 답하기 위해 다음 도구가 필요합니다:",
                                #     parent_id=reasoning_step.id
                                # ).send()
                                
                                # 각 도구 호출에 대한 상세 정보
                                # for i, tool_call in enumerate(last_msg.tool_calls, 1):
                                #     await cl.Message(
                                #         content=f"**도구 {i}**: `{tool_call['name']}`\n"
                                #                f"**이유**: {'PDF 문서에서 관련 내용을 찾기 위해' if 'pdf' in tool_call['name'].lower() else '관련 법령을 검색하기 위해'}\n"
                                #                f"**검색 매개변수**:\n```json\n{json.dumps(tool_call['args'], indent=2, ensure_ascii=False)}\n```",
                                #         parent_id=reasoning_step.id
                                #     ).send()
                                
                                reasoning_step.output = f"선택된 도구: {', '.join(tool_names)}"
                            step_count += 1
                        else:
                            # 최종 응답 생성 단계
                            async with cl.Step(name=f"✨ 최종 답변", type="run") as final_step:
                                final_step.input = "수집된 모든 정보"
                                # await cl.Message(
                                #     content="🧠 모든 정보를 종합하여 최종 답변을 작성합니다...\n\n"
                                #            "📋 **고려사항**:\n"
                                #            "• PDF 문서의 내용\n"
                                #            "• 관련 법령 조항\n"
                                #            "• 법적 해석 및 조언",
                                #     parent_id=final_step.id
                                # ).send()
                                final_response = last_msg.content
                                final_step.output = "답변 생성 완료"
                            step_count += 1
                    
                    # PDF 도구 실행 단계 - 별도 Step
                    elif node_name == "pdf_tools":
                        async with cl.Step(name=f"📄 PDF 문서 검색", type="tool") as pdf_step:
                            pdf_step.input = "PDF 문서에서 관련 정보 검색"
                            
                            # 도구 실행 전 메시지
                            # await cl.Message(
                            #     content="업로드된 PDF에서 관련 내용을 찾고 있습니다...",
                            #     parent_id=pdf_step.id
                            # ).send()
                            
                            # PDF 도구 실행 결과 상세 표시
                            # ai_message = cast(AIMessage, value["messages"][-2] if len(value["messages"]) > 1 else last_msg)
                            # if hasattr(ai_message, 'tool_calls') and ai_message.tool_calls:
                            #     for tool_call in ai_message.tool_calls:
                            #         if 'pdf' in tool_call['name'].lower():
                            #             await cl.Message(
                            #                 content=f"🔧 **실행 중인 도구**: `{tool_call['name']}`",
                            #                 parent_id=pdf_step.id
                            #             ).send()
                            
                            # 도구 결과 표시
                            if isinstance(last_msg, ToolMessage):
                                content_str = str(last_msg.content)
                                pdf_step.output = f"PDF에서 관련 내용을 찾았습니다, ({len(content_str)})"
                            else:
                                pdf_step.output = "PDF 검색 완료"
                        step_count += 1
                    
                    # 법령 도구 실행 단계 - 별도 Step
                    elif node_name == "law_tools":
                        async with cl.Step(name=f"⚖️ 법령 데이터베이스 검색", type="tool") as law_step:
                            law_step.input = "관련 법령 조항 검색"
                            
                            # 도구 실행 전 메시지
                            # await cl.Message(
                            #     content="📚 법령 데이터베이스에서 관련 조항을 찾고 있습니다...",
                            #     parent_id=law_step.id
                            # ).send()
                            
                            # 법령 도구 실행 결과 상세 표시
                            # ai_message = cast(AIMessage, value["messages"][-2] if len(value["messages"]) > 1 else last_msg)
                            # if hasattr(ai_message, 'tool_calls') and ai_message.tool_calls:
                            #     for tool_call in ai_message.tool_calls:
                            #         if 'law' in tool_call['name'].lower():
                            #             await cl.Message(
                            #                 content=f"🔍 **검색어**: `{tool_call['args'].get('query', '알 수 없음')}`\n"
                            #                        f"🔧 **실행 중인 도구**: `{tool_call['name']}`",
                            #                 parent_id=law_step.id
                            #             ).send()
                            
                            # 도구 결과 표시
                            if isinstance(last_msg, ToolMessage):
                                content_str = str(last_msg.content)
                                content_preview = content_str[:300] + "..." if len(content_str) > 300 else content_str
                                await cl.Message(
                                    content=f"📜 **법령 검색 결과**:\n```\n{content_preview}\n```",
                                    parent_id=law_step.id
                                ).send()
                                law_step.output = f"관련 법령 조항 내용을 찾았습니다. ({len(content_str)})"
                            else:
                                law_step.output = "법령 검색 완료"
                        step_count += 1
        
        return final_response


# 전역 챗봇 인스턴스 (향상된 버전)
chatbot = ChainlitLawChatbot()


@cl.on_chat_start
async def on_chat_start():
    """채팅 시작 시 실행"""
    await cl.Message(
        content="⚖️ **약관톡톡**에 오신 것을 환영합니다!\n\n"
                "📋 **사용 방법:**\n"
                "1. 📄 PDF 문서를 업로드하여 분석을 시작하세요\n"
                "2. 💬 질문을 보내면 AI의 추론 과정을 실시간으로 볼 수 있습니다\n"
                "3. 🔍 각 단계별 도구 사용과 결과를 확인할 수 있습니다\n"
                "4. 📚 모든 답변은 구체적인 법령 조항을 근거로 작성됩니다\n\n"
                "**📁 PDF를 업로드하여 시작하세요!**",
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """메시지 처리 (향상된 CoT 포함)"""
    # 파일 업로드와 메시지를 동시에 처리
    if message.elements:
        # 파일 업로드 처리 (기존 로직과 동일)
        await handle_file_upload(message.elements)
        
        if message.content and message.content.strip():
            import asyncio
            await asyncio.sleep(1)  # PDF 초기화 완료 대기
            
            if chatbot.current_pdf_file and pdf_reader.is_chromadb_initialized():
                await process_user_query_with_cot(message.content)
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
    
    # 사용자 메시지 처리 (CoT 포함)
    await process_user_query_with_cot(message.content)


async def process_user_query_with_cot(user_input: str):
    """Chain of Thought를 포함한 사용자 쿼리 처리 함수"""
    try:
        # 향상된 CoT로 메시지 처리
        response = await chatbot.process_message_with_cot(
            user_input, 
            pdf_initialized=True, 
            law_initialized=True
        )
        
        # 최종 응답과 PDF 첨부 전송
        if response:
            elements = []
            # PDF가 로드되어 있으면 인라인으로 첨부
            if chatbot.current_pdf_file and os.path.exists(chatbot.current_pdf_file):
                elements.append(
                    cl.Pdf(
                        name=os.path.basename(chatbot.current_pdf_file),
                        path=chatbot.current_pdf_file,
                        display="side"
                    )
                )
            
            await cl.ElementSidebar.set_elements(elements)
            await cl.ElementSidebar.set_title("PDF Preview")
            
            await cl.Message(
                content=f"💬 **최종 답변**\n\n{response}",
                elements=elements
            ).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ 오류가 발생했습니다: {str(e)}\n\n다시 시도해주세요."
        ).send()


async def handle_file_upload(elements: List):
    """파일 업로드 처리 (기존과 동일)"""
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
                    
                    # 파일 정보 표시
                    await cl.Message(
                        content=f"📄 PDF 업로드 완료: {element.name} ({file_size:,} bytes)"
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
