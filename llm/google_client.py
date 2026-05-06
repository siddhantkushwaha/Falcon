import os

import google.generativeai as genai

from llm.base import LLMClient


class GoogleAILLMClient(LLMClient):
    def __init__(self, model: str = "gemini-2.0-flash", api_key_env: str = "GOOGLE_AI_API_KEY"):
        super().__init__(model)
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Environment variable '{api_key_env}' not set")
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model)

    def generate(self, prompt: str) -> str:
        response = self.client.generate_content(prompt)
        return response.text
