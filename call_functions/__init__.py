"""Utility tools for the chatbot."""
from importlib import import_module
from typing import Any

__all__ = ["pdf_reader", "law_api", "pdf_highlighter"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        module = import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")
