import ollama

from llm.base import LLMClient


class OllamaLLMClient(LLMClient):
    def __init__(self, model: str, host: str):
        super().__init__(model)
        self.client = ollama.Client(host=host)

    def generate(self, prompt: str) -> str:
        response = self.client.generate(prompt=prompt, model=self.model)
        return response["response"]
