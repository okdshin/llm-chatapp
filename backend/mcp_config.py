import json
from dataclasses import dataclass
from typing import Dict


@dataclass
class MCPServerConfig:
    command: str
    args: list[str]


def load_mcp_config(config_path: str) -> Dict[str, MCPServerConfig]:
    """Load MCP server configurations from a JSON file

    Args:
        config_path: Path to the JSON config file

    Returns:
        Dict mapping server IDs to their configurations

    Raises:
        FileNotFoundError: If config file is not found
        json.JSONDecodeError: If config file is not valid JSON
    """
    with open(config_path) as f:
        config = json.load(f)
        return {
            server_id: MCPServerConfig(
                command=server_config["command"], args=server_config["args"]
            )
            for server_id, server_config in config["mcpServers"].items()
        }
