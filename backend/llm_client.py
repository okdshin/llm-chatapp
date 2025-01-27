import os
from typing import List, Dict, Any, Optional, AsyncGenerator, Union, Tuple
from litellm import acompletion
import logging
import json

logger = logging.getLogger(__name__)


def _format_tools_for_litellm(
    tools: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Format MCP tools to LiteLLM format"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tools
    ]


class LLMClient:
    def __init__(self):
        self.model = os.getenv("DEFAULT_MODEL", "claude-3-haiku-latest")
        self.temperature = float(os.getenv("TEMPERATURE", 0.7))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))

    async def get_streaming_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_manager=None,
    ) -> Union[Tuple[List[Dict[str, Any]], Any], AsyncGenerator[str, None]]:
        """Get response from LLM with tool calling support"""
        try:
            formatted_tools = _format_tools_for_litellm(tools) if tools else None
            return self._handle_streaming_response(messages, formatted_tools, tool_manager)
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            raise

    async def _handle_streaming_response(
        self,
        messages: List[Dict[str, str]],
        formatted_tools: Optional[List[Dict[str, Any]]],
        tool_manager,
    ) -> AsyncGenerator[str, None]:
        """Handle streaming response from LLM"""
        response = await acompletion(
            model=self.model,
            messages=messages,
            tools=formatted_tools,
            tool_choice="auto",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        # Handle content chunks
        async for chunk in response:
            # Handle regular content
            if chunk.choices[0].delta.content:
                yield "content", chunk.choices[0].delta.content
                continue

            # Handle tool calls
            tool_calls = getattr(chunk.choices[0].delta, "tool_calls", None)
            if not tool_calls:
                continue

            tool_call = tool_calls[0]
            if tool_call.id:
                assert tool_call.function.name
                yield "tool_call_id", tool_call.id
                yield "tool_name", tool_call.function.name
            if tool_call.function.arguments:
                yield "tool_args", tool_call.function.arguments


async def interactive_chat(llm_client: LLMClient, mcp_manager):
    """Run an interactive chat loop with tool support"""
    print("\nChat Started!")
    print("Type your messages or 'quit' to exit.")

    # Get available tools
    tools = await mcp_manager.list_all_tools()
    logger.debug(f"Available tools: {json.dumps(tools, indent=2)}")

    messages = []
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == "quit":
                break

            # Add user message to history
            messages.append({"role": "user", "content": user_input})

            while True:
                print(f"{messages=}")

                # Get response with tool support
                response = await llm_client.get_streaming_response(
                    messages=messages,
                    tools=tools,
                    tool_manager=mcp_manager,
                )

                print("\nAssistant:", end=" ")
                content_chunks = []
                tool_calls = []
                tool_call_id = None
                tool_name = None
                tool_arguments_chunks = []
                async for chunk_type, chunk in response:
                    if chunk_type == "content":
                        print(chunk, end="", flush=True)
                        content_chunks.append(chunk)
                    elif chunk_type == "tool_call_id":
                        tool_call_id = chunk
                    elif chunk_type == "tool_name":
                        print(f"\ntool_name: {chunk}, arguments: ", end="", flush=True)
                        if tool_name is not None:
                            assert tool_call_id
                            tool_calls.append(
                                dict(
                                    id=tool_call_id,
                                    name=tool_name,
                                    arguments="".join(tool_arguments_chunks)
                                )
                            )
                        tool_name = chunk
                    elif chunk_type == "tool_args":
                        print(chunk, end="", flush=True)
                        tool_arguments_chunks.append(chunk)
                if tool_name is not None:
                    assert tool_call_id
                    tool_calls.append(
                        dict(
                            id=tool_call_id,
                            name=tool_name,
                            arguments="".join(tool_arguments_chunks)
                        )
                    )
                    print()

                if not tool_calls:
                    break

                tool_messages = []
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = json.loads(tool_call["arguments"])
                    print("tool_call", f"[Calling tool {tool_name} with args {tool_args}]")
                    try:
                        result = await mcp_manager.call_tool(tool_name, tool_args)
                        print("tool_result", f"[Tool result: {result}]")
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        logger.error(error_msg)
                        print("tool_error", f"[{error_msg}]")
                    tool_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_call["name"],
                            "content": json.dumps(result.content[0].text),
                        }
                    )
                assistant_message = {
                    "finish_reason": 'tool_calls',
                    "index": 0,
                    "role": "assistant",
                    "content": "".join(content_chunks),
                    "tool_calls": [{
                        "id": tool_call["id"],
                        "type": "function",
                        "function": {
                            "name": tool_call["name"],
                            "arguments": tool_call["arguments"],
                        },
                    } for tool_call in tool_calls],
                }
                messages.append(assistant_message)
                messages.extend(tool_messages)
                print()

        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    from mcp_config import load_mcp_config
    from mcp_client import MCPClientManager
    import dotenv
    import asyncio

    dotenv.load_dotenv()

    async def main():
        # 設定の読み込みとMCPマネージャーの初期化
        configs = load_mcp_config("mcp_config.json")
        llm_client = LLMClient()

        async with MCPClientManager(configs) as mcp_manager:
            # 対話セッションの開始（ストリーミングモード）
            await interactive_chat(llm_client, mcp_manager)

    asyncio.run(main())
