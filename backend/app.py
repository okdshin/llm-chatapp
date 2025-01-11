from flask import Flask, request, jsonify, send_from_directory
import os
import sys

def get_static_folder():
    # 実行ファイルかPythonスクリプトかを判断
    if getattr(sys, 'frozen', False):
        # Nuitkaでビルドされた実行ファイルの場合
        application_path = os.path.dirname(sys.executable)
    else:
        # 通常のPythonスクリプトの場合
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.abspath(os.path.join(application_path, '..', 'frontend', 'dist'))

app = Flask(__name__, static_folder=get_static_folder())

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