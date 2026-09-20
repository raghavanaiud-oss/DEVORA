from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RuntimeConfig:
    name: str
    extension: str
    command: List[str]
    docker_image: str
    default_entrypoint: str


SUPPORTED_RUNTIMES: Dict[str, RuntimeConfig] = {
    "python": RuntimeConfig(
        name="python",
        extension=".py",
        command=["python", "-u"],
        docker_image="python:3.11-alpine",
        default_entrypoint="main.py",
    ),
    "javascript": RuntimeConfig(
        name="javascript",
        extension=".js",
        command=["node"],
        docker_image="node:20-alpine",
        default_entrypoint="index.js",
    ),
    "typescript": RuntimeConfig(
        name="typescript",
        extension=".ts",
        command=["npx", "ts-node"],
        docker_image="node:20-alpine",
        default_entrypoint="index.ts",
    ),
}


def detect_runtime(filename: str, language: Optional[str] = None) -> RuntimeConfig:
    if language and language.lower() in SUPPORTED_RUNTIMES:
        return SUPPORTED_RUNTIMES[language.lower()]

    lower_name = filename.lower()
    if lower_name.endswith(".py"):
        return SUPPORTED_RUNTIMES["python"]
    elif lower_name.endswith(".js") or lower_name.endswith(".mjs"):
        return SUPPORTED_RUNTIMES["javascript"]
    elif lower_name.endswith(".ts"):
        return SUPPORTED_RUNTIMES["typescript"]

    # Default fallback
    return SUPPORTED_RUNTIMES["python"]
