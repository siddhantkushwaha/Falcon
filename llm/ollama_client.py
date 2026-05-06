import ollama

from llm.base import LLMClient


class OllamaLLMClient(LLMClient):
    def __init__(self, model: str = "phi3"):
        super().__init__(model)

    def generate(self, prompt: str) -> str:
        response = ollama.generate(prompt=prompt, model=self.model)
        return response["response"]
