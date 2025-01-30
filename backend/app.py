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
from typing import AsyncGenerator, Dict, Any, Optional
from dataclasses import dataclass

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

@dataclass
class ChatManager:
    """Chat management class"""
    llm_client: LLMClient
    mcp_manager: Optional[Any] = None
    sessions: Dict[str, ChatSession] = None

    def __post_init__(self):
        self.sessions = {}

    def get_or_create_session(self, chat_id: str, chunk_processor: ChunkProcessor) -> ChatSession:
        if chat_id not in self.sessions:
            self.sessions[chat_id] = ChatSession(
                llm_client=self.llm_client,
                mcp_manager=self.mcp_manager,
                chunk_processor=chunk_processor
            )
        else:
            # Update chunk processor for existing session
            self.sessions[chat_id].chunk_processor = chunk_processor
        return self.sessions[chat_id]


class SSEChunkProcessor(ChunkProcessor):
    """Server-Sent Events chunk processor"""
    def __init__(self):
        self.chunks = []

    async def process_chunk(self, chunk: ChunkData) -> None:
        """Process a chunk and yield SSE formatted data"""
        if chunk.type == "content":
            yield f"data: {json.dumps({'content': chunk.content})}\n\n"
        elif chunk.type in ["tool_name", "tool_args"]:
            yield f"data: {json.dumps({'type': chunk.type, 'content': chunk.content})}\n\n"


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
                chat_data = load_chat(filename[:-5])  # Remove .json extension
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

        # Process message
        response = await session.llm_client.get_streaming_response(
            messages=session.messages,
            tools=None,  # No tools for now
        )

        # Stream response
        async for chunk_type, chunk in response:
            chunk_data = ChunkData(type=chunk_type, content=chunk)
            async for event in chunk_processor.process_chunk(chunk_data):
                yield event

        # Save chat after processing
        assistant_message = {
            "role": "assistant",
            "content": "".join(chunk.content for chunk in chunk_processor.chunks if isinstance(chunk, ChunkData) and chunk.type == "content"),
            "timestamp": datetime.now().isoformat()
        }
        chat_data["messages"].append(assistant_message)
        save_chat(chat_id, chat_data)

        yield "data: {\"done\": true}\n\n"

    except Exception as e:
        logger.error(f"Error in process_chat_message: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


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

        return Response(
            stream_with_context(process_chat_message(app.chat_manager, chat_id, user_message)),
            content_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}")
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
    return response


def create_app(mcp_manager=None):
    """Create and configure application instance"""
    app.chat_manager = ChatManager(
        llm_client=LLMClient(),
        mcp_manager=mcp_manager
    )
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5000)