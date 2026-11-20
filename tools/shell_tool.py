"""Compatibility entry point for bounded workspace operations."""
from tools.base_tool import BaseTool
from security.audit_logger import AuditLogger
from security.path_guard import PathGuard
from security.shell_guard import ShellGuard


class ShellTool(BaseTool):
    name = "shell"
    description = "Operaciones locales de lectura: pwd, echo, ls y cat."
    parameters = {
        "type": "object",
        "properties": {"command": {"type": "string", "description": "Operación local de lectura"}},
        "required": ["command"],
    }

    def __init__(self, base_dir=None):
        self.guard = ShellGuard()
        self.workspace = PathGuard(base_dir)
        self.audit = AuditLogger()

    def execute(self, command: str):
        operation = "denied"
        status = "OK"
        try:
            operation, args = self.guard.parse(command)
            if operation == "pwd":
                result = str(self.workspace.base_dir)
            elif operation == "echo":
                result = " ".join(args)
            elif operation == "ls":
                result = "\n".join(self.workspace.list(args[0] if args else "."))
            else:
                result = self.workspace.read(args[0])
        except (ValueError, OSError):
            status = "DENIED"
            result = "ERROR: comando bloqueado por seguridad o archivo no disponible."
        self.audit.log(tool="shell", arguments={"operation": operation}, result=status)
        return result
