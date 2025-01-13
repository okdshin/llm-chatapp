import asyncio
from mcp_client import MCPClientManager
from mcp_config import load_mcp_config
import json

async def main():
    # Load configurations
    configs = load_mcp_config('mcp_config.json')
    
    # Create manager with loaded configs
    async with MCPClientManager(configs) as manager:
        # List all available tools
        all_tools = await manager.list_all_tools()
        print("\nAvailable tools with detailed information:")
        print(json.dumps(all_tools, indent=2))

if __name__ == "__main__":
    asyncio.run(main())