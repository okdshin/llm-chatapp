import asyncio
from typing import Dict, Optional, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

from .mcp_config import MCPServerConfig

load_dotenv()


class MCPClient:
    def __init__(self, config: MCPServerConfig):
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
        self._tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]
        print(f"\nConnected to server with tools:", [tool["name"] for tool in self._tools])

    async def list_tools(self) -> List[dict]:
        """List available tools from the server"""
        if self._tools is None:
            raise RuntimeError("Client not connected to server")
        return self._tools

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
            server_id: MCPClient(config)
            for server_id, config in server_configs.items()
        }
        self._connected = False

    async def __aenter__(self):
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_all()

    async def connect_all(self):
        """Connect to all configured servers"""
        if self._connected:
            return

        for server_id, client in self.clients.items():
            try:
                await self.exit_stack.enter_async_context(client)
            except Exception as e:
                print(f"Failed to connect to server {server_id}: {e}")
                continue

        self._connected = True

    def get_client(self, server_id: str) -> MCPClient:
        """Get client by server ID
        
        Args:
            server_id: Server identifier
            
        Returns:
            MCPClient: Client instance
            
        Raises:
            KeyError: If server_id is not found
        """
        if server_id not in self.clients:
            raise KeyError(f"No client found for server: {server_id}")
        return self.clients[server_id]

    async def list_all_tools(self) -> Dict[str, List[dict]]:
        """List tools from all connected servers
        
        Returns:
            Dict mapping server IDs to their available tools
        """
        if not self._connected:
            raise RuntimeError("Clients are not connected. Call connect_all() first.")

        tools_by_server = {}
        for server_id, client in self.clients.items():
            try:
                tools_by_server[server_id] = await client.list_tools()
            except Exception as e:
                print(f"Failed to list tools for server {server_id}: {e}")
        return tools_by_server

    async def cleanup_all(self):
        """Clean up all client resources"""
        await self.exit_stack.aclose()
        self._connected = False


if __name__ == "__main__":
    from .mcp_config import load_mcp_config
    
    async def main():
        # Load configurations
        configs = load_mcp_config('mcp_config.json')
        
        # Create manager with loaded configs
        async with MCPClientManager(configs) as manager:
            # List tools from all servers
            all_tools = await manager.list_all_tools()
            print("\nAvailable tools by server:")
            for server_id, tools in all_tools.items():
                print(f"\n{server_id}:")
                for tool in tools:
                    print(f"- {tool['name']}: {tool['description']}")

            # Get specific client example
            filesystem_client = manager.get_client('filesystem')
            filesystem_tools = await filesystem_client.list_tools()
            print("\nFilesystem tools:", [tool['name'] for tool in filesystem_tools])

    asyncio.run(main())
