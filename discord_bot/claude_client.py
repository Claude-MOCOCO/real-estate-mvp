"""Claude API + MCP Client 브릿지 — Tool Use Loop 관리"""

import os
import json
import asyncio
from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class PropertyAssistant:
    def __init__(self):
        self.anthropic = AsyncAnthropic()
        self.mcp_session: ClientSession | None = None
        self.tools_schema: list[dict] = []
        self._stdio_context = None

    async def connect_mcp(self, server_path: str):
        """MCP 서버 연결 + Tool 스키마 수집"""
        server_params = StdioServerParameters(
            command="python", args=[server_path]
        )
        self._stdio_context = stdio_client(server_params)
        transport = await self._stdio_context.__aenter__()
        self.mcp_session = ClientSession(*transport)
        await self.mcp_session.initialize()

        # MCP Tool 목록 -> Claude tools 파라미터 형식으로 변환
        tools = await self.mcp_session.list_tools()
        self.tools_schema = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in tools.tools
        ]

    async def disconnect_mcp(self):
        """MCP 서버 연결 해제 — 봇 종료 시 반드시 호출하여 좀비 프로세스 방지"""
        if self.mcp_session:
            self.mcp_session = None
        if self._stdio_context:
            await self._stdio_context.__aexit__(None, None, None)
            self._stdio_context = None

    async def chat(self, user_message: str, history: list[dict]) -> str:
        """자연어 메시지 -> Tool Use Loop -> 최종 응답"""
        messages = history + [{"role": "user", "content": user_message}]

        system_prompt = (
            "당신은 부동산 매물 관리 어시스턴트입니다. "
            "사용자의 자연어 질문을 이해하고, 적절한 도구를 사용하여 "
            "매물 검색, 등록, 수정, 삭제, 통계, 비교를 수행합니다. "
            "한국어로 친절하게 응답하세요. "
            "가격은 억/만원 단위로, 면적은 m²와 평을 병기하세요."
        )

        response = await self.anthropic.messages.create(
            model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
            max_tokens=4096,
            system=system_prompt,
            tools=self.tools_schema,
            messages=messages,
        )

        # Tool Use Loop (최대 5회)
        loop_count = 0
        while response.stop_reason == "tool_use" and loop_count < 5:
            loop_count += 1
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue
                try:
                    result = await asyncio.wait_for(
                        self.mcp_session.call_tool(block.name, block.input),
                        timeout=30.0,
                    )
                    # MCP SDK Content 객체에서 텍스트 추출 후 직렬화
                    content_text = "\n".join(
                        c.text for c in result.content if hasattr(c, "text")
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content_text,
                    })
                except asyncio.TimeoutError:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({
                            "error": "timeout",
                            "message": "도구 호출 시간 초과 (30초)"
                        }),
                        "is_error": True,
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({
                            "error": "tool_error",
                            "message": str(e)
                        }),
                        "is_error": True,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = await self.anthropic.messages.create(
                model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
                max_tokens=4096,
                system=system_prompt,
                tools=self.tools_schema,
                messages=messages,
            )

        # 최종 텍스트 추출
        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
