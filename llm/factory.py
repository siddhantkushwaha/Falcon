from llm.base import LLMClient
from llm.ollama_client import OllamaLLMClient
from llm.google_client import GoogleAILLMClient


def get_llm_client(config: dict) -> LLMClient:
    provider = config["provider"]
    models = config["model"]

    if provider == "ollama":
        return OllamaLLMClient(model=models["ollama"], host=config["ollama_host"])
    elif provider == "google":
        return GoogleAILLMClient(
            model=models["google"],
            api_key=config["google_api_key"],
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
