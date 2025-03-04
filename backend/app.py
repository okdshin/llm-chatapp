from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    Response,
    stream_with_context,
)
import os
import json
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from .llm_client import LLMClient, ChatSession, ChunkProcessor, ChunkData
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass
import asyncio

# 環境変数のロード
load_dotenv()

# ベースパスの設定
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_PATH = os.path.join(BASE_PATH, "frontend", "dist")
CHATS_DIR = os.path.join(BASE_PATH, "chats")

# アプリケーションの初期化
app = Flask(__name__, static_folder=STATIC_PATH)
if not os.path.exists(CHATS_DIR):
    os.makedirs(CHATS_DIR)

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class ChatManager:
    """Chat management class"""
    llm_client: LLMClient
    mcp_manager: Optional[Any] = None
    sessions: Dict[str, ChatSession] = None
    tools: List[Dict] = None

    def __post_init__(self):
        self.sessions = {}

    async def initialize(self):
        """Initialize chat manager and load tools"""
        if self.mcp_manager:
            self.tools = await self.mcp_manager.list_all_tools()
            logger.info(f"Loaded {len(self.tools)} tools")
            
    def get_or_create_session(self, chat_id: str, chunk_processor: ChunkProcessor) -> ChatSession:
        """Get existing chat session or create a new one"""
        if chat_id not in self.sessions:
            self.sessions[chat_id] = ChatSession(
                llm_client=self.llm_client,
                mcp_manager=self.mcp_manager,
                chunk_processor=chunk_processor
            )
        return self.sessions[chat_id]


def create_app(mcp_manager=None):
    """Create and configure application instance"""
    chat_manager = ChatManager(
        llm_client=LLMClient(),
        mcp_manager=mcp_manager
    )
    app.chat_manager = chat_manager
    return app, chat_manager


class SSEChunkProcessor(ChunkProcessor):
    """Server-Sent Events chunk processor"""
    def __init__(self):
        self.chunks = []

    async def process_chunk(self, chunk: ChunkData) -> None:
        """Process a chunk and store it"""
        if chunk.type == "content":
            self.chunks.append(chunk.content)
        elif chunk.type in ["tool_name", "tool_args"]:
            self.chunks.append({chunk.type: chunk.content})


def load_chat(chat_id: str) -> Dict[str, Any]:
    """Load chat history from file"""
    try:
        chat_path = os.path.join(CHATS_DIR, f"{chat_id}.json")
        if not os.path.exists(chat_path):
            return {
                "id": chat_id,
                "messages": [],
                "created_at": datetime.now().isoformat()
            }
        
        with open(chat_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading chat {chat_id}: {e}")
        raise


def save_chat(chat_id: str, data: Dict[str, Any]) -> None:
    """Save chat history to file"""
    try:
        with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), "w") as f:
            json.dump(data, f)
            logger.debug(f"Chat {chat_id} saved successfully")
    except Exception as e:
        logger.error(f"Error saving chat {chat_id}: {e}")
        raise


def list_chats():
    """List all available chats"""
    try:
        chats = []
        for filename in os.listdir(CHATS_DIR):
            if filename.endswith(".json"):
                chat_data = load_chat(filename[:-5])
                chats.append({
                    "id": chat_data["id"],
                    "created_at": chat_data["created_at"],
                    "preview": (
                        chat_data["messages"][0]["content"][:50]
                        if chat_data["messages"]
                        else "New chat"
                    ),
                })
        return sorted(chats, key=lambda x: x["created_at"], reverse=True)
    except Exception as e:
        logger.error(f"Error listing chats: {e}")
        raise


async def process_chat_message(
    chat_manager: ChatManager,
    chat_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """Process a chat message and generate streaming response"""
    try:
        logger.debug(f"Starting process_chat_message for chat {chat_id}")
        chat_data = load_chat(chat_id)
        
        # Add user message
        chat_data["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        # Create chunk processor and get session
        chunk_processor = SSEChunkProcessor()
        session = chat_manager.get_or_create_session(chat_id, chunk_processor)
        session.messages = chat_data["messages"]

        while True:
            logger.debug("Starting new iteration of chat processing loop")
            # Process message with tools
            response = await session.llm_client.get_streaming_response(
                messages=session.messages,
                tools=chat_manager.tools,
                tool_manager=chat_manager.mcp_manager,
            )

            content_chunks = []
            tool_calls = []
            current_tool = {"id": None, "name": None, "arguments": ""}

            # Process response chunks
            async for chunk_type, chunk in response:
                logger.debug(f"Processing chunk: type={chunk_type}, content={chunk[:100] if isinstance(chunk, str) and len(chunk) > 100 else chunk}")
                chunk_data = ChunkData(type=chunk_type, content=chunk)
                await chunk_processor.process_chunk(chunk_data)

                if chunk_type == "content":
                    content_chunks.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                elif chunk_type == "tool_call_id":
                    if current_tool["name"]:
                        logger.debug(f"Adding completed tool call: {current_tool}")
                        tool_calls.append(current_tool.copy())
                    current_tool = {"id": chunk, "name": None, "arguments": ""}
                elif chunk_type == "tool_name":
                    current_tool["name"] = chunk
                    logger.debug(f"Tool call started: {chunk}")
                    yield f"data: {json.dumps({'type': 'tool_call', 'name': chunk})}\n\n"
                elif chunk_type == "tool_args":
                    current_tool["arguments"] = chunk

            # Add the last tool call if exists
            if current_tool["name"]:
                logger.debug(f"Adding final tool call: {current_tool}")
                tool_calls.append(current_tool.copy())

            # If no tool calls, break the loop
            if not tool_calls:
                logger.debug("No more tool calls, breaking loop")
                break

            # Create assistant message with tool calls
            assistant_message = {
                "role": "assistant",
                "content": "".join(content_chunks),
                "tool_calls": [{
                    "id": tool_call["id"],
                    "type": "function",
                    "function": {
                        "name": tool_call["name"],
                        "arguments": tool_call["arguments"],
                    },
                } for tool_call in tool_calls]
            }
            session.messages.append(assistant_message)

            # Process tool calls and get results
            logger.debug(f"Processing {len(tool_calls)} tool calls")
            tool_messages = await session.process_tool_calls(tool_calls)
            
            if tool_messages:
                logger.debug(f"Received {len(tool_messages)} tool messages")
                session.messages.extend(tool_messages)
                for msg in tool_messages:
                    logger.debug(f"Tool message: {msg}")
                    yield f"data: {json.dumps({'type': 'tool_result', 'content': msg['content']})}\n\n"
            else:
                logger.debug("No tool messages received, breaking loop")
                break

            logger.debug("Completed tool processing loop iteration")

        # Save final assistant message
        assistant_message = {
            "role": "assistant",
            "content": "".join(content_chunks),
            "timestamp": datetime.now().isoformat()
        }
        logger.debug("Saving final assistant message")
        chat_data["messages"].append(assistant_message)
        save_chat(chat_id, chat_data)

        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        logger.error(f"Error in process_chat_message: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def process_async_gen(agen):
    """Process an async generator in a synchronous context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def gen():
        try:
            while True:
                try:
                    yield loop.run_until_complete(agen.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()
    
    return gen()


# API Routes
@app.route("/api/chats", methods=["GET"])
def get_chats():
    """Get list of all chats"""
    return jsonify(list_chats())


@app.route("/api/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    """Get specific chat history"""
    return jsonify(load_chat(chat_id))


@app.route("/api/chats/<chat_id>/messages", methods=["POST"])
def add_message(chat_id):
    """Add message to chat and get streaming response"""
    try:
        user_message = request.json.get("message", "")
        logger.debug(f"Received message for chat {chat_id}: {user_message[:50]}...")

        agen = process_chat_message(app.chat_manager, chat_id, user_message)
        return Response(
            stream_with_context(process_async_gen(agen)),
            content_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# Static file routes
@app.route("/")
def serve_frontend():
    """Serve frontend static files"""
    try:
        return app.send_static_file("index.html")
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        return str(e), 500


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serve static assets"""
    try:
        return send_from_directory(os.path.join(app.static_folder, "assets"), filename)
    except Exception as e:
        logger.error(f"Error serving asset {filename}: {e}")
        return str(e), 500


@app.after_request
def after_request(response):
    """Add headers for SSE support"""
    if response.mimetype == "text/event-stream":
        response.headers.add("Cache-Control", "no-cache")
        response.headers.add("X-Accel-Buffering", "no")
        response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__ == "__main__":
    app = create_app()[0]
    app.run(port=5000)