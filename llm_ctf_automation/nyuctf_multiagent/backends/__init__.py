from .openai_backend import OpenAIBackend
from .anthropic_backend import AnthropicBackend
from .together_backend import TogetherBackend
from .gemini_backend import GeminiBackend
from .backend import Role

BACKENDS = [OpenAIBackend, AnthropicBackend, TogetherBackend, GeminiBackend]
MODELS = {m: b for b in BACKENDS for m in b.MODELS}


def resolve_backend_cls(model, config=None):
    if model in MODELS:
        return MODELS[model]
    if config is not None and getattr(config, "openai_base_url", None):
        return OpenAIBackend
    raise KeyError(f"Model {model} not in options. Select from {', '.join(MODELS.keys())}")
