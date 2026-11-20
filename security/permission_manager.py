"""Policy for tools automatically callable from a model."""
MODEL_TOOLS = frozenset({"time", "calculator", "shell", "file"})


class PermissionManager:
    def requires_confirmation(self, tool: str) -> bool:
        return tool not in MODEL_TOOLS
