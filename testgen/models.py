"""Creates the Gemini chat model and embedding model (both free with a Google AI Studio key)."""
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from testgen import config


class MissingAPIKeyError(RuntimeError):
    pass


def _require_key() -> str:
    if not config.GOOGLE_API_KEY:
        raise MissingAPIKeyError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your key "
            "from https://aistudio.google.com/apikey"
        )
    return config.GOOGLE_API_KEY


def _chat_model(name: str, temperature: float) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=name,
        google_api_key=_require_key(),
        temperature=temperature,
        timeout=config.REQUEST_TIMEOUT,
        max_retries=config.MAX_RETRIES,
    )


def get_llm(temperature: float = 0.3, model: str | None = None, use_fallback: bool = True):
    """Low temperature = consistent, focused output (a little creativity helps find edge cases).

    Has a timeout and few retries, and switches to FALLBACK_MODEL if the main model fails.
    Pass `model` to pick a specific model, and use_fallback=False to test one model alone.
    """
    name = model or config.CHAT_MODEL
    primary = _chat_model(name, temperature)
    if use_fallback and config.FALLBACK_MODEL and config.FALLBACK_MODEL != name:
        return primary.with_fallbacks([_chat_model(config.FALLBACK_MODEL, temperature)])
    return primary


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        google_api_key=_require_key(),
    )
