from flask import Flask, request, jsonify, send_from_directory
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='../frontend/dist')

# チャット履歴を保存するディレクトリ
CHATS_DIR = 'chats'
if not os.path.exists(CHATS_DIR):
    os.makedirs(CHATS_DIR)

def load_chat(chat_id):
    try:
        with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"id": chat_id, "messages": [], "created_at": datetime.now().isoformat()}

def save_chat(chat_id, data):
    with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), 'w') as f:
        json.dump(data, f)

def list_chats():
    chats = []
    for filename in os.listdir(CHATS_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(CHATS_DIR, filename), 'r') as f:
                chat_data = json.load(f)
                chats.append({
                    "id": chat_data["id"],
                    "created_at": chat_data["created_at"],
                    "preview": chat_data["messages"][0]["content"][:50] if chat_data["messages"] else "New chat"
                })
    return sorted(chats, key=lambda x: x["created_at"], reverse=True)

@app.route('/api/chats', methods=['GET'])
def get_chats():
    return jsonify(list_chats())

@app.route('/api/chats/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    return jsonify(load_chat(chat_id))

@app.route('/api/chats/<chat_id>/messages', methods=['POST'])
def add_message(chat_id):
    data = request.json
    user_message = data.get('message', '')
    
    chat_data = load_chat(chat_id)
    
    # ユーザーメッセージを追加
    chat_data["messages"].append({
        'role': 'user',
        'content': user_message,
        'timestamp': datetime.now().isoformat()
    })
    
    # ここに実際のClaude APIとの連携コードを追加します
    response = "This is a sample response"
    
    # アシスタントの応答を追加
    chat_data["messages"].append({
        'role': 'assistant',
        'content': response,
        'timestamp': datetime.now().isoformat()
    })
    
    save_chat(chat_id, chat_data)
    return jsonify({'response': response})

@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)

if __name__ == '__main__':
    app.run(port=5000)