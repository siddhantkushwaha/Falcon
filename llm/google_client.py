import os

from google import genai

from llm.base import LLMClient


class GoogleAILLMClient(LLMClient):
    def __init__(self, model: str, api_key_env: str):
        super().__init__(model)
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Environment variable '{api_key_env}' not set")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return response.text
