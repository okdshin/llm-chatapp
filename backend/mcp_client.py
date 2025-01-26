import asyncio
import logging
from typing import Dict, Optional, List, Any, Tuple
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_config import MCPServerConfig


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def make_prefixed_tool_name(server_id: str, tool_name: str) -> str:
    """Create a prefixed tool name from server_id and original tool name"""
    return f"{server_id}_{tool_name}"


class MCPClient:
    def __init__(self, server_id: str, config: MCPServerConfig):
        self.server_id = server_id
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.config = config
        self._tools: Optional[List[dict]] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def connect(self):
        """Connect to MCP server"""
        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
        )
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        await self.session.initialize()

        # Cache available tools
        response = await self.session.list_tools()
        logger.debug(f"Raw tools from server {self.server_id}: {response.tools}")

        self._tools = [
            {
                "name": make_prefixed_tool_name(self.server_id, tool.name),
                "description": tool.description,
                "input_schema": tool.inputSchema,
                "original_name": tool.name,
            }
            for tool in response.tools
        ]
        logger.debug(f"Processed tools for server {self.server_id}: {self._tools}")

    async def list_tools(self) -> List[dict]:
        """List available tools from the server"""
        if self._tools is None:
            raise RuntimeError("Client not connected to server")
        return self._tools

    async def call_tool(self, tool_name: str, tool_args: Any) -> Any:
        """Call a specific tool with given arguments

        Args:
            tool_name: Original name of the tool (without server_id prefix)
            tool_args: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If client is not connected
            ValueError: If tool_name is not found
        """
        if self.session is None:
            raise RuntimeError("Client not connected to server")

        logger.debug(f"Calling tool {tool_name} with args: {tool_args}")
        return await self.session.call_tool(tool_name, tool_args)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


class MCPClientManager:
    def __init__(self, server_configs: Dict[str, MCPServerConfig]):
        """Initialize MCP client manager with server configurations

        Args:
            server_configs: Dict mapping server IDs to their configurations
        """
        self.exit_stack = AsyncExitStack()
        self.clients: Dict[str, MCPClient] = {
            server_id: MCPClient(server_id, config)
            for server_id, config in server_configs.items()
        }
        self._tool_mapping: Dict[str, Tuple[str, str]] = (
            {}
        )  # prefixed_name -> (server_id, original_name)
        self._connected = False

    async def __aenter__(self):
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_all()

    def _split_tool_name(self, prefixed_name: str) -> Tuple[str, str]:
        """Split prefixed tool name into server_id and original tool name"""
        if prefixed_name not in self._tool_mapping:
            logger.error(
                f"Tool {prefixed_name} not found in mapping. Available tools: {self._tool_mapping}"
            )
            raise ValueError(f"Unknown tool: {prefixed_name}")
        return self._tool_mapping[prefixed_name]

    async def connect_all(self):
        """Connect to all configured servers and build tool mapping"""
        if self._connected:
            return

        for server_id, client in self.clients.items():
            try:
                await self.exit_stack.enter_async_context(client)
                # Update tool mapping after successful connection
                tools = await client.list_tools()
                logger.debug(f"Tools from server {server_id}: {tools}")

                for tool in tools:
                    self._tool_mapping[tool["name"]] = (
                        server_id,
                        tool["original_name"],
                    )

                logger.debug(f"Updated tool mapping: {self._tool_mapping}")

            except Exception as e:
                logger.error(f"Failed to connect to server {server_id}: {e}")
                continue

        self._connected = True

    async def list_all_tools(self) -> List[dict]:
        """List all available tools from all servers

        Returns:
            List of all available tools with prefixed names
        """
        if not self._connected:
            raise RuntimeError("Clients are not connected. Call connect_all() first.")

        all_tools = []
        for client in self.clients.values():
            try:
                tools = await client.list_tools()
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"Failed to list tools for server {client.server_id}: {e}")
        return all_tools

    async def call_tool(self, prefixed_tool_name: str, tool_args: Any) -> Any:
        """Call a specific tool using its prefixed name

        Args:
            prefixed_tool_name: Tool name with server_id prefix (e.g., "filesystem_list_directory")
            tool_args: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool name is not found
            RuntimeError: If clients are not connected
        """
        if not self._connected:
            raise RuntimeError("Clients are not connected. Call connect_all() first.")

        logger.debug(
            f"Attempting to call tool: {prefixed_tool_name} with args: {tool_args}"
        )
        server_id, original_name = self._split_tool_name(prefixed_tool_name)
        logger.debug(f"Resolved to server: {server_id}, original tool: {original_name}")

        return await self.clients[server_id].call_tool(original_name, tool_args)

    async def call_tools(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Call multiple tools

        Args:
            tool_calls: List of tool call specifications, each containing:
                - tool_name: Prefixed tool name (e.g., "filesystem_list_directory")
                - tool_args: Arguments to pass to the tool

        Returns:
            List of results, each containing:
                - tool_name: Prefixed tool name
                - result: Tool execution result
                - error: Error message if the call failed (optional)
        """
        if not self._connected:
            raise RuntimeError("Clients are not connected. Call connect_all() first.")

        results = []
        for call in tool_calls:
            prefixed_name = call["tool_name"]
            try:
                result = await self.call_tool(prefixed_name, call["tool_args"])
                results.append({"tool_name": prefixed_name, "result": result})
            except Exception as e:
                logger.error(f"Error calling tool {prefixed_name}: {e}", exc_info=True)
                results.append({"tool_name": prefixed_name, "error": str(e)})
        return results

    async def cleanup_all(self):
        """Clean up all client resources"""
        await self.exit_stack.aclose()
        self._connected = False


if __name__ == "__main__":
    from mcp_config import load_mcp_config
    import json

    async def main():
        # Load configurations
        configs = load_mcp_config("mcp_config.json")

        # Create manager with loaded configs
        async with MCPClientManager(configs) as manager:
            # List all available tools
            all_tools = await manager.list_all_tools()
            print("\nAvailable tools:")
            for tool in all_tools:
                print(f"- {tool['name']}: {tool['description']}")

            print("\nTool mapping:", json.dumps(manager._tool_mapping, indent=2))

            # Example tool calls
            tool_calls = [
                {"tool_name": "filesystem_list_directory", "tool_args": {"path": "/"}},
                {
                    "tool_name": "web-search_search",
                    "tool_args": {"query": "Python MCP"},
                },
            ]

            results = await manager.call_tools(tool_calls)
            for result in results:
                if "error" in result:
                    print(f"\nError calling {result['tool_name']}: {result['error']}")
                else:
                    print(f"\nResult from {result['tool_name']}:", result["result"])

    asyncio.run(main())
