1. DONE ~~최종 LLM 답변이 function call인 경우 call request만 하고 답변 없이 끝나버림, tool call 없을 때까지 closed state graph 유지~~
2. DONE ~~get_env assertion 안 거치고 env variables 들여오는 경우 있음~~
3. branch merge
4. DONE ~~`LawVectorStore.vector_store`가 None인 경우 있음 (assertion err 걸리는게 보임)~~
5. `search_law_by_query` 재검색이 안됨, 이거 말고도 기타 함수들 세션유지가 안되는 듯? 
    ```[tool/error] [chain:LangGraph > chain:law_tools > tool:search_law_by_query] [133ms] Tool run errored with error:
    ValueError("Error raised by inference endpoint: HTTPSConnectionPool(host='sylph-wsl.ragdoll-ule.ts.net', port=443): Max retries exceeded with url: /api/embeddings (Caused by NewConnectionError('<urllib3.connection.HTTPSConnection object at 0x7505ac9d2de0>: Failed to establish a new connection: [Errno 111] Connection refused'))")
    ```
    아마 그냥 `langchain_chroma.Chroma`로 다 바꿔야할 듯, `langchain_community`버전 지원 이미 종료했음