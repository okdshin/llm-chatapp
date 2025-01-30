import webview
import logging
import argparse
import asyncio
from typing import Optional
from backend.mcp_config import load_mcp_config
from backend.mcp_client import MCPClientManager
from backend.app import create_app
import signal
from contextlib import asynccontextmanager


def setup_logger(debug_mode: bool) -> logging.Logger:
    """Set up logging configuration"""
    level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Chat App')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--window-debug', action='store_true', help='Enable webview debug mode')
    parser.add_argument('--port', type=int, default=5000, help='Port number (default: 5000)')
    parser.add_argument('--width', type=int, default=1024, help='Window width (default: 1024)')
    parser.add_argument('--height', type=int, default=768, help='Window height (default: 768)')
    parser.add_argument('--mcp-config', type=str, default='mcp_config.json',
                       help='Path to MCP configuration file')
    return parser.parse_args()


def on_shown(logger: logging.Logger) -> None:
    """Handle window shown event"""
    logger.info("Window shown")


@asynccontextmanager
async def create_mcp_manager(config_path: str):
    """Create and manage MCP client lifecycle"""
    configs = load_mcp_config(config_path)
    async with MCPClientManager(configs) as manager:
        yield manager


def main():
    """Main application entry point"""
    args = parse_args()
    logger = setup_logger(args.debug)
    logger.info(f"Starting app with debug={args.debug}, window-debug={args.window_debug}")

    # Initialize event loop and MCP manager
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def setup_app():
        async with create_mcp_manager(args.mcp_config) as mcp_manager:
            # Create and configure Flask app
            app, chat_manager = create_app(mcp_manager)
            app.debug = args.debug

            # Initialize chat manager
            await chat_manager.initialize()
            
            # Create window
            window = webview.create_window(
                'Chat App',
                app,
                width=args.width,
                height=args.height,
                min_size=(800, 600)
            )
            
            # Set up event handlers
            window.events.shown += lambda: on_shown(logger)
            
            # Define cleanup handler
            def cleanup(signum, frame):
                loop.stop()
                
            # Register signal handlers
            signal.signal(signal.SIGINT, cleanup)
            signal.signal(signal.SIGTERM, cleanup)
            
            # Start webview
            webview.start(
                debug=args.window_debug,
                http_port=args.port
            )

    try:
        loop.run_until_complete(setup_app())
    finally:
        loop.close()


if __name__ == '__main__':
    main()