import os
from typing import List, Dict, Any, Optional, AsyncGenerator, Union, Tuple, Protocol, Callable, Awaitable
from litellm import acompletion
import logging
import json
from dataclasses import dataclass

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


@dataclass
class ChunkData:
    type: str
    content: str


class ChunkProcessor(Protocol):
    """Protocol for chunk processors"""
    async def process_chunk(self, chunk: ChunkData) -> None:
        """Process a single chunk of data"""
        ...


class DefaultChunkProcessor:
    """Default implementation that prints chunks to console"""
    async def process_chunk(self, chunk: ChunkData) -> None:
        if chunk.type == "content":
            print(chunk.content, end="", flush=True)
        elif chunk.type == "tool_name":
            print(f"\ntool_name: {chunk.content}, arguments: ", end="", flush=True)
        elif chunk.type == "tool_args":
            print(chunk.content, end="", flush=True)


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
        completion_args = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        if formatted_tools:
            completion_args.update({
                "tools": formatted_tools,
                "tool_choice": "auto"
            })

        response = await acompletion(**completion_args)

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


class ChatSession:
    def __init__(self, llm_client: LLMClient, mcp_manager, chunk_processor: ChunkProcessor):
        self.llm_client = llm_client
        self.mcp_manager = mcp_manager
        self.chunk_processor = chunk_processor
        self.messages = []
        self.logger = logging.getLogger(__name__)

    async def process_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """Process tool calls and generate tool messages"""
        tool_messages = []
        for tool_call in tool_calls:
            tool_message = await self._execute_tool_call(tool_call)
            if tool_message:
                tool_messages.append(tool_message)
        return tool_messages

    async def _execute_tool_call(self, tool_call: Dict) -> Optional[Dict]:
        """Execute a single tool call and return the corresponding message"""
        tool_name = tool_call["name"]
        try:
            tool_args = json.loads(tool_call["arguments"])
            self.logger.debug(f"Calling tool {tool_name} with args {tool_args}")
            
            result = await self.mcp_manager.call_tool(tool_name, tool_args)
            self.logger.debug(f"Tool result: {result}")
            
            return {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_name,
                "content": json.dumps(result.content[0].text),
            }
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return None

    def create_assistant_message(self, content_chunks: List[str], tool_calls: List[Dict]) -> Dict:
        """Create an assistant message with tool calls"""
        return {
            "finish_reason": "tool_calls" if tool_calls else "stop",
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
            } for tool_call in tool_calls] if tool_calls else [],
        }

    async def process_llm_response(self, response) -> Tuple[List[str], List[Dict]]:
        """Process LLM response and collect content chunks and tool calls"""
        content_chunks = []
        tool_calls = []
        current_tool = {"id": None, "name": None, "arguments": []}

        async for chunk_type, chunk in response:
            # Create ChunkData and process it
            chunk_data = ChunkData(type=chunk_type, content=chunk)
            await self.chunk_processor.process_chunk(chunk_data)

            # Store chunks and tool calls
            if chunk_type == "content":
                content_chunks.append(chunk)
            else:
                await self._handle_tool_chunk(chunk_type, chunk, current_tool, tool_calls)

        if current_tool["name"]:  # Add the last tool call if exists
            tool_calls.append(self._create_tool_call(current_tool))

        return content_chunks, tool_calls

    async def _handle_tool_chunk(self, chunk_type: str, chunk: str, 
                                current_tool: Dict, tool_calls: List[Dict]) -> None:
        """Handle different types of tool chunks in the response"""
        if chunk_type == "tool_call_id":
            if current_tool["name"]:  # Save previous tool call if exists
                tool_calls.append(self._create_tool_call(current_tool))
            current_tool.update({"id": chunk, "name": None, "arguments": []})
        
        elif chunk_type == "tool_name":
            current_tool["name"] = chunk
        
        elif chunk_type == "tool_args":
            current_tool["arguments"].append(chunk)

    @staticmethod
    def _create_tool_call(tool_info: Dict) -> Dict:
        """Create a tool call dictionary from tool info"""
        return {
            "id": tool_info["id"],
            "name": tool_info["name"],
            "arguments": "".join(tool_info["arguments"])
        }


async def interactive_chat(
    llm_client: LLMClient,
    mcp_manager,
    chunk_processor: Optional[ChunkProcessor] = None
):
    """Run an interactive chat loop with tool support"""
    print("\nChat Started!")
    print("Type your messages or 'quit' to exit.")

    # Use default chunk processor if none provided
    chunk_processor = chunk_processor or DefaultChunkProcessor()
    
    session = ChatSession(llm_client, mcp_manager, chunk_processor)
    tools = await mcp_manager.list_all_tools()
    logger.debug(f"Available tools: {json.dumps(tools, indent=2)}")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == "quit":
                break

            session.messages.append({"role": "user", "content": user_input})
            await process_chat_turn(session, tools)

        except Exception as e:
            logger.error(f"Error in chat loop: {str(e)}")
            print(f"\nError: {str(e)}")


async def process_chat_turn(session: ChatSession, tools: List[Dict]):
    """Process a single turn in the chat conversation"""
    while True:
        print("\nAssistant:", end=" ")
        
        response = await session.llm_client.get_streaming_response(
            messages=session.messages,
            tools=tools,
            tool_manager=session.mcp_manager,
        )

        content_chunks, tool_calls = await session.process_llm_response(response)
        
        if not tool_calls:
            break

        assistant_message = session.create_assistant_message(content_chunks, tool_calls)
        tool_messages = await session.process_tool_calls(tool_calls)
        
        session.messages.append(assistant_message)
        session.messages.extend(tool_messages)
        print()


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