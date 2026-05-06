from llm.base import LLMClient
from llm.ollama_client import OllamaLLMClient
from llm.google_client import GoogleAILLMClient


def get_llm_client(config: dict) -> LLMClient:
    provider = config["provider"]
    models = config["model"]

    if provider == "ollama":
        return OllamaLLMClient(model=models.get("ollama", "phi3"))
    elif provider == "google":
        return GoogleAILLMClient(
            model=models.get("google", "gemini-2.0-flash"),
            api_key_env=config.get("google_api_key_env", "GOOGLE_AI_API_KEY"),
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
