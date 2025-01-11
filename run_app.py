import webview
import threading
import subprocess
import time
import os

def run_flask():
    if os.name == 'nt':  # Windows
        python_path = os.path.join('backend', 'venv', 'Scripts', 'python')
    else:  # Unix/Linux/Mac
        python_path = os.path.join('backend', 'venv', 'bin', 'python')
    
    flask_app = os.path.join('backend', 'app.py')
    subprocess.Popen([python_path, flask_app])

def main():
    # Start Flask server
    run_flask()
    
    # Wait for Flask to start
    time.sleep(2)
    
    # Create and start webview window
    webview.create_window('Chat App', 'http://localhost:5000', width=800, height=600)
    webview.start()

if __name__ == '__main__':
    main()