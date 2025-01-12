import os
from typing import List, Dict, Any, Generator
from litellm import completion
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.model = os.getenv('DEFAULT_MODEL', 'claude-3-sonnet-20240229')
        self.temperature = float(os.getenv('TEMPERATURE', 0.7))
        
    def get_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            raise

    def get_streaming_response(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """ストリーミングレスポンスを取得"""
        try:
            logger.debug(f"Starting streaming response with model {self.model}")
            response = completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                stream=True
            )

            for chunk in response:
                if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        logger.debug(f"Received chunk: {content[:50]}...")
                        yield content

        except Exception as e:
            logger.error(f"Error getting streaming LLM response: {e}")
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