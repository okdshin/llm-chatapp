from backend.app import app
import webview
import logging
import argparse

def setup_logger(debug_mode):
    level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Chat App')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--window-debug', action='store_true', help='Enable webview debug mode')
    parser.add_argument('--port', type=int, default=5000, help='Port number (default: 5000)')
    parser.add_argument('--width', type=int, default=800, help='Window width (default: 800)')
    parser.add_argument('--height', type=int, default=600, help='Window height (default: 600)')
    return parser.parse_args()

def on_shown(logger):
    logger.info("Window shown")
    logger.info(f"Static folder: {app.static_folder}")
    logger.info(f"Debug mode: {app.debug}")

if __name__ == '__main__':
    args = parse_args()
    
    # Flaskのデバッグモード設定
    app.debug = args.debug
    
    # ロガーのセットアップ
    logger = setup_logger(args.debug)
    logger.info(f"Starting app with debug={args.debug}, window-debug={args.window_debug}")
    
    # ウィンドウ作成
    window = webview.create_window(
        'Chat App',
        app,
        width=args.width,
        height=args.height
    )
    
    # イベントハンドラの設定
    window.events.shown += lambda: on_shown(logger)
    
    # webviewの起動
    webview.start(
        debug=args.window_debug,
        http_port=args.port
    )