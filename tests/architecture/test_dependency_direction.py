"""Enforce dependency direction for the hexagonal architecture."""

import ast
from pathlib import Path

CORE_DIRECTORIES = (Path("app/domain"), Path("app/ports"), Path("app/services"))
FORBIDDEN_PREFIXES = (
    "app.api",
    "app.adapters",
    "app.bootstrap",
    "fastapi",
    "pydantic",
    "qdrant_client",
    "redis",
    "rq",
    "sentence_transformers",
)


def test_core_does_not_import_external_modules():
    violations: list[str] = []
    for directory in CORE_DIRECTORIES:
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                module = None
                if isinstance(node, ast.ImportFrom):
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(FORBIDDEN_PREFIXES):
                            violations.append(
                                f"{path}:{node.lineno} imports {alias.name}"
                            )
                if module and module.startswith(FORBIDDEN_PREFIXES):
                    violations.append(f"{path}:{node.lineno} imports {module}")

    assert violations == []
