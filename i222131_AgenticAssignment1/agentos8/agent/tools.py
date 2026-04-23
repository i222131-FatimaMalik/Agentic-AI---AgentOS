from __future__ import annotations
from typing import Any, Dict, Protocol, runtime_checkable

@runtime_checkable
class Tool(Protocol):
    name: str
    def run(self, args: Dict[str, Any]) -> str: ...

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list_names(self):
        return sorted(self._tools.keys())

    def run(self, name: str, args: Dict[str, Any]) -> str:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name].run(args)
