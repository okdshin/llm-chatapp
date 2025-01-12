import os
from typing import List, Dict, Any
from litellm import completion
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.model = os.getenv('DEFAULT_MODEL', 'claude-3-sonnet-20240229')
        self.temperature = float(os.getenv('TEMPERATURE', 0.7))
        
    async def get_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = await completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            raise

    def format_messages(self, chat_history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """ChatアプリのメッセージフォーマットをLiteLLM形式に変換"""
        formatted_messages = []
        for msg in chat_history:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return formatted_messages