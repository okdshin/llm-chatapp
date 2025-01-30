import webview
import logging
import argparse
import asyncio
import threading
from typing import Optional
from backend.mcp_config import load_mcp_config
from backend.mcp_client import MCPClientManager
from backend.app import create_app


class MCPManager:
    """Manage MCP client lifecycle"""
    def __init__(self, config_path: str, logger: logging.Logger):
        self.config_path = config_path
        self.logger = logger
        self.manager: Optional[MCPClientManager] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._startup_event = threading.Event()
        self._manager_instance = []

    def __enter__(self):
        """Start MCP manager thread and return manager instance"""
        def run_async_loop():
            self.logger.info("Starting MCP manager thread")
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            async def setup_manager():
                configs = load_mcp_config(self.config_path)
                self.manager = MCPClientManager(configs)
                manager = await self.manager.__aenter__()
                self._manager_instance.append(manager)
                self._startup_event.set()
                self.logger.info("MCP manager initialized")
                
                # Wait for shutdown signal
                while not self._shutdown_event.is_set():
                    await asyncio.sleep(0.1)
                
                # Cleanup in the same task
                if self.manager:
                    await self.manager.__aexit__(None, None, None)

            try:
                self._event_loop.run_until_complete(setup_manager())
            except Exception as e:
                self.logger.error(f"Error in MCP manager thread: {e}")
                self._startup_event.set()
                raise
            finally:
                if not self._event_loop.is_closed():
                    remaining_tasks = asyncio.all_tasks(self._event_loop)
                    if remaining_tasks:
                        self._event_loop.run_until_complete(asyncio.gather(*remaining_tasks))
                    self._event_loop.close()
                self.logger.info("MCP manager thread stopped")

        self._thread = threading.Thread(target=run_async_loop, daemon=True)
        self._thread.start()
        
        self._startup_event.wait()
        return self._manager_instance[0] if self._manager_instance else None

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up MCP manager resources"""
        self.logger.info("Stopping MCP manager...")
        self._shutdown_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                self.logger.warning("MCP manager thread did not stop cleanly")
            else:
                self.logger.info("MCP manager stopped successfully")


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


def main():
    """Main application entry point"""
    args = parse_args()
    logger = setup_logger(args.debug)
    logger.info(f"Starting app with debug={args.debug}, window-debug={args.window_debug}")

    with MCPManager(args.mcp_config, logger) as mcp_client:
        app = create_app(mcp_client)
        app.debug = args.debug
        
        window = webview.create_window(
            'Chat App',
            app,
            width=args.width,
            height=args.height,
            min_size=(800, 600)
        )
        
        window.events.shown += lambda: on_shown(logger)
        
        webview.start(
            debug=args.window_debug,
            http_port=args.port
        )


if __name__ == '__main__':
    main()