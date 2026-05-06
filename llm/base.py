import json
import re
from abc import ABC, abstractmethod


class LLMClient(ABC):
    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send prompt to LLM, return raw text response."""
        pass

    def generate_json(self, prompt: str) -> list | dict | None:
        """Send prompt and parse response as JSON."""
        raw = self.generate(prompt)
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str):
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            for i, ch in enumerate(text):
                if ch in "[{":
                    try:
                        return json.loads(text[i:])
                    except json.JSONDecodeError:
                        continue
            return None
