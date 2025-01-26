import os
from typing import List, Dict, Any, Optional, AsyncGenerator
from litellm import acompletion
import logging
import json

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.model = os.getenv("DEFAULT_MODEL", "claude-3-haiku-latest")
        self.temperature = float(os.getenv("TEMPERATURE", 0.7))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))

    def _format_tools_for_litellm(
        self, tools: List[Dict[str, Any]]
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

    async def get_response_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_manager=None,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Get response from LLM with tool calling support"""
        try:
            formatted_tools = self._format_tools_for_litellm(tools) if tools else None

            if not stream:
                # Non-streaming mode
                response = await acompletion(
                    model=self.model,
                    messages=messages,
                    tools=formatted_tools,
                    tool_choice="auto",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=False,
                )
                logger.info(f"{response=}")
                tool_call_message = response.choices[0].message

                tool_results = []

                # Handle tool calls if present in the response
                tool_calls = response.choices[0].message.tool_calls
                if not tool_calls:
                    # If no tool calls, just return the response content
                    return response.choices[0].message.content

                tool_result_messages = []
                for tool_call in tool_calls:
                    function_call = tool_call.function
                    tool_name = function_call.name
                    try:
                        tool_args = json.loads(function_call.arguments)
                    except json.JSONDecodeError:
                        logger.error(
                            f"Invalid tool arguments: {function_call.arguments}"
                        )
                        continue

                    logger.info(f"Calling tool {tool_name} with args: {tool_args}")

                    try:
                        # Execute tool call using MCPClientManager
                        result = await tool_manager.call_tool(tool_name, tool_args)
                        print(type(result), result)
                        tool_results.append({"call": tool_name, "result": result})

                        # Add tool result to conversation
                        tool_result_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": result.content[0].text,
                        })

                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        logger.error(error_msg)

                # Get follow-up response from the model
                follow_up_response = await acompletion(
                    model=self.model,
                    messages=messages + [tool_call_message] + tool_result_messages,
                    tools=formatted_tools,
                    tool_choice="auto",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=False,
                )

                return [tool_call_message] + tool_result_messages, follow_up_response

            else:
                # Streaming mode
                async def stream_generator() -> AsyncGenerator[str, None]:
                    current_tool_call = {"name": None, "arguments": ""}
                    content_buffer = ""

                    response = await acompletion(
                        model=self.model,
                        messages=messages,
                        tools=formatted_tools,
                        tool_choice="auto",
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        stream=True,
                    )

                    async for chunk in response:
                        # Handle content chunks
                        if (
                            hasattr(chunk.choices[0].delta, "content")
                            and chunk.choices[0].delta.content
                        ):
                            content = chunk.choices[0].delta.content
                            content_buffer += content
                            yield content

                        # Handle tool call chunks
                        if hasattr(chunk.choices[0].delta, "tool_calls"):
                            tool_calls = chunk.choices[0].delta.tool_calls
                            for tool_call in tool_calls:
                                # Accumulate tool name and arguments
                                if hasattr(tool_call.function, "name"):
                                    current_tool_call["name"] = tool_call.function.name
                                if hasattr(tool_call.function, "arguments"):
                                    current_tool_call[
                                        "arguments"
                                    ] += tool_call.function.arguments

                                # If we have both name and complete arguments, execute the tool
                                if (
                                    current_tool_call["name"]
                                    and current_tool_call["arguments"]
                                    and current_tool_call["arguments"].endswith("}")
                                ):
                                    try:
                                        tool_args = json.loads(
                                            current_tool_call["arguments"]
                                        )
                                        tool_name = current_tool_call["name"]

                                        yield f"\n[Calling tool {tool_name} with args {tool_args}]\n"

                                        result = await tool_manager.call_tool(
                                            tool_name, tool_args
                                        )
                                        yield f"[Tool result: {result}]\n"

                                        # Add tool result to conversation
                                        messages.append(
                                            {
                                                "role": "assistant",
                                                "content": content_buffer,
                                                "tool_calls": [
                                                    {
                                                        "id": tool_call.id,
                                                        "function": {
                                                            "name": tool_name,
                                                            "arguments": json.dumps(
                                                                tool_args
                                                            ),
                                                        },
                                                    }
                                                ],
                                            }
                                        )
                                        messages.append(
                                            {
                                                "role": "tool",
                                                "tool_call_id": tool_call.id,
                                                "content": json.dumps(result),
                                            }
                                        )

                                        # Get follow-up response from the model
                                        follow_up_response = await acompletion(
                                            model=self.model,
                                            messages=messages,
                                            tools=formatted_tools,
                                            tool_choice="auto",
                                            temperature=self.temperature,
                                            max_tokens=self.max_tokens,
                                            stream=True,
                                        )

                                        async for follow_chunk in follow_up_response:
                                            if (
                                                hasattr(
                                                    follow_chunk.choices[0].delta,
                                                    "content",
                                                )
                                                and follow_chunk.choices[
                                                    0
                                                ].delta.content
                                            ):
                                                yield follow_chunk.choices[
                                                    0
                                                ].delta.content

                                        # Reset tool call buffer
                                        current_tool_call = {
                                            "name": None,
                                            "arguments": "",
                                        }
                                        content_buffer = ""

                                    except Exception as e:
                                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                                        logger.error(error_msg)
                                        yield f"[{error_msg}]\n"

                                        # Reset tool call buffer
                                        current_tool_call = {
                                            "name": None,
                                            "arguments": "",
                                        }
                                        content_buffer = ""

                return stream_generator()

        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            raise


async def interactive_chat(llm_client: LLMClient, mcp_manager, stream: bool = True):
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

            print(f"{messages=}")

            # Get response with tool support
            new_messages, response = await llm_client.get_response_with_tools(
                messages=messages,
                tools=tools,
                tool_manager=mcp_manager,
                stream=stream,
            )
            messages.extend(new_messages)

            print("\nAssistant:", end=" ")
            if stream:
                chunks = []
                async for chunk in response:
                    print(chunk, end="", flush=True)
                    chunks.append(chunk)
                print()
                messages.append({"role": "assistant", "content": "".join(chunks)})
            else:
                print(response)
                messages.append({"role": "assistant", "content": response})

        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    from mcp_config import load_mcp_config
    from mcp_client import MCPClientManager
    import asyncio

    async def main():
        # 設定の読み込みとMCPマネージャーの初期化
        configs = load_mcp_config("mcp_config.json")
        llm_client = LLMClient()

        async with MCPClientManager(configs) as mcp_manager:
            # 対話セッションの開始（ストリーミングモード）
            await interactive_chat(llm_client, mcp_manager, stream=False)

    asyncio.run(main())
