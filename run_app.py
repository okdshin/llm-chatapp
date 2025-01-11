from backend.app import app
import webview

if __name__ == '__main__':
    webview.create_window('Chat App', app, width=800, height=600)
    webview.start()