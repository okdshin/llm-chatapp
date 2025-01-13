import asyncio
from dataclasses import dataclass
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


@dataclass
class MCPServerConfig:
    command: str
    args: list[str]


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_servers(self, config: MCPServerConfig):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        server_params = StdioServerParameters(
            command=config.command, args=config.args,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def list_tools(self):
        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]
        return available_tools

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


if __name__ == "__main__":
    async def main():
        try:
            client = MCPClient()
            await client.connect_to_servers(
                MCPServerConfig(
                    command="npx",
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        "/home/okada/claude_workspace",
                    ],
                ),
            )
            await client.list_tools()
        finally:
            await client.cleanup()

    asyncio.run(main())
