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
from .llm_client import LLMClient

# 環境変数のロード
load_dotenv()


# 実行ファイルのパスを取得する関数
def get_base_path():
    if getattr(sys, "frozen", False):
        # Nuitkaでビルドされた場合のパス
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 通常の実行時のパス
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ベースパスの設定
BASE_PATH = get_base_path()

# 静的ファイルのパスを設定
STATIC_PATH = os.path.join(BASE_PATH, "frontend", "dist")

app = Flask(__name__, static_folder=STATIC_PATH)

# チャット履歴を保存するディレクトリ
CHATS_DIR = os.path.join(BASE_PATH, "chats")
if not os.path.exists(CHATS_DIR):
    os.makedirs(CHATS_DIR)

# ロガーの取得
logger = logging.getLogger(__name__)

# LLMクライアントの初期化
llm_client = LLMClient()


def load_chat(chat_id):
    try:
        with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.debug(f"Chat {chat_id} not found, creating new chat")
        return {"id": chat_id, "messages": [], "created_at": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error loading chat {chat_id}: {e}")
        raise


def save_chat(chat_id, data):
    try:
        with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), "w") as f:
            json.dump(data, f)
            logger.debug(f"Chat {chat_id} saved successfully")
    except Exception as e:
        logger.error(f"Error saving chat {chat_id}: {e}")
        raise


def list_chats():
    try:
        chats = []
        for filename in os.listdir(CHATS_DIR):
            if filename.endswith(".json"):
                with open(os.path.join(CHATS_DIR, filename), "r") as f:
                    chat_data = json.load(f)
                    chats.append(
                        {
                            "id": chat_data["id"],
                            "created_at": chat_data["created_at"],
                            "preview": (
                                chat_data["messages"][0]["content"][:50]
                                if chat_data["messages"]
                                else "New chat"
                            ),
                        }
                    )
        return sorted(chats, key=lambda x: x["created_at"], reverse=True)
    except Exception as e:
        logger.error(f"Error listing chats: {e}")
        raise


@app.route("/api/chats", methods=["GET"])
def get_chats():
    return jsonify(list_chats())


@app.route("/api/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    return jsonify(load_chat(chat_id))


def stream_response(chat_id: str, user_message: str):
    try:
        chat_data = load_chat(chat_id)
        current_time = datetime.now().isoformat()

        # ユーザーメッセージを追加
        chat_data["messages"].append(
            {"role": "user", "content": user_message, "timestamp": current_time}
        )

        # アシスタントの応答を準備
        messages = llm_client.format_messages(chat_data["messages"])
        full_response = ""

        # ストリーミングレスポンスを取得
        for chunk in llm_client.get_streaming_response(messages):
            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # 完全な応答をチャット履歴に保存
        chat_data["messages"].append(
            {
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now().isoformat(),
            }
        )
        save_chat(chat_id, chat_data)

        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        logger.error(f"Error in stream_response: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.route("/api/chats/<chat_id>/messages", methods=["POST"])
def add_message(chat_id):
    try:
        data = request.json
        user_message = data.get("message", "")
        stream = data.get("stream", False)  # デフォルトはストリーミングなし
        logger.debug(f"Received message for chat {chat_id}: {user_message[:50]}...")

        if stream:
            return Response(
                stream_with_context(stream_response(chat_id, user_message)),
                content_type="text/event-stream",
            )
        else:
            chat_data = load_chat(chat_id)

            # ユーザーメッセージを追加
            chat_data["messages"].append(
                {
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # LLMクライアントを使用して応答を取得
            messages = llm_client.format_messages(chat_data["messages"])
            response = llm_client.get_response(messages)

            # アシスタントの応答を追加
            chat_data["messages"].append(
                {
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            save_chat(chat_id, chat_data)
            return jsonify({"response": response})

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/")
def serve_frontend():
    try:
        return app.send_static_file("index.html")
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        logger.error(f"Static folder path: {app.static_folder}")
        return f"Error: {str(e)}", 500


@app.after_request
def after_request(response):
    if response.content_type == "text/event-stream":
        response.headers.add("Cache-Control", "no-cache")
        response.headers.add("X-Accel-Buffering", "no")
    return response


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    try:
        return send_from_directory(os.path.join(app.static_folder, "assets"), filename)
    except Exception as e:
        logger.error(f"Error serving asset {filename}: {e}")
        return f"Error: {str(e)}", 500


# デバッグ用エンドポイント
@app.route("/debug/paths")
def debug_paths():
    return {
        "base_path": BASE_PATH,
        "static_folder": app.static_folder,
        "chats_dir": CHATS_DIR,
        "exists": {
            "static_folder": os.path.exists(app.static_folder),
            "index_html": os.path.exists(os.path.join(app.static_folder, "index.html")),
            "chats_dir": os.path.exists(CHATS_DIR),
        },
        "debug_mode": app.debug,
        "llm_config": {
            "model": llm_client.model,
            "temperature": llm_client.temperature,
        },
    }


if __name__ == "__main__":
    app.run(port=5000)
