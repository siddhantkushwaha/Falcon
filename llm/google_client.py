from google import genai

from llm.base import LLMClient


class GoogleAILLMClient(LLMClient):
    def __init__(self, model: str, api_key: str):
        super().__init__(model)
        if not api_key:
            raise ValueError("google_api_key is not set in config")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model, contents=prompt
        )
        return response.text
