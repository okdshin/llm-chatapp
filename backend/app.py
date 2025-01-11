from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='../frontend/dist')

messages = []

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    # ここに実際のClaude APIとの連携コードを追加します
    response = "This is a sample response"  
    
    messages.append({
        'role': 'user',
        'content': user_message
    })
    messages.append({
        'role': 'assistant',
        'content': response
    })
    
    return jsonify({'response': response})

@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)

# 開発時のみ使用
if __name__ == '__main__':
    app.run(port=5000)