"""Minimal smoke check for core dependency imports."""

from __future__ import annotations

import importlib


CORE_IMPORTS = {
    "mcp": "mcp",
    "python-dotenv": "dotenv",
    "langchain": "langchain",
    "langchain-core": "langchain_core",
    "langchain-openai": "langchain_openai",
    "langgraph": "langgraph",
    "pandas": "pandas",
    "numpy": "numpy",
    "sqlalchemy": "sqlalchemy",
    "pyyaml": "yaml",
    "psycopg2-binary": "psycopg2",
    "typing-extensions": "typing_extensions",
}


def main() -> None:
    for package, module_name in CORE_IMPORTS.items():
        importlib.import_module(module_name)
    print("Edit this line to practice a tiny Git change.")


if __name__ == "__main__":
    main()
