"""
ARUS
Tool Manager
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import tools

from tools.base_tool import BaseTool
from security.audit_logger import AuditLogger
from security.permission_manager import MODEL_TOOLS, PermissionManager

MAX_ARGUMENT_LENGTH = 4096


class ToolManager:

    def __init__(self):

        self.tools = {}
        self.permissions = PermissionManager()

        self.load_tools()


    def load_tools(self):

        for _, module_name, _ in pkgutil.iter_modules(tools.__path__):

            if module_name in (
                "base_tool",
                "tool_manager",
            ):
                continue

            module = importlib.import_module(
                f"tools.{module_name}"
            )

            for _, obj in inspect.getmembers(
                module,
                inspect.isclass,
            ):

                if (
                    issubclass(obj, BaseTool)
                    and obj is not BaseTool
                ):

                    tool = obj()
                    self.tools[tool.name] = tool


    def register(self, tool):
        """
        Fase 15: permite añadir una herramienta ya instanciada (p.ej.
        aportada por un plugin) sin pasar por el escaneo de
        `tools/`. No sustituye `load_tools()` -- es aditivo.
        """

        if tool.name in self.tools or tool.name in MODEL_TOOLS:
            raise ValueError(f"No se puede reemplazar la herramienta '{tool.name}'.")
        self.tools[tool.name] = tool

    def execute(
        self,
        name,
        *args,
        **kwargs,
    ):

        if name not in self.tools:

            raise ValueError(
                f"Herramienta '{name}' no encontrada."
            )

        tool = self.tools[name]
        if self.permissions.requires_confirmation(name):
            AuditLogger().log(tool="policy", arguments={"tool": name}, result="DENIED")
            return "ERROR: herramienta bloqueada. Requiere autorización humana."
        try:
            arguments = inspect.signature(tool.execute).bind(*args, **kwargs).arguments
        except TypeError:
            return "ERROR: argumentos inválidos."
        if any(isinstance(value, str) and len(value) > MAX_ARGUMENT_LENGTH for value in arguments.values()):
            return "ERROR: argumento demasiado largo."
        if name == "file" and (arguments.get("action") != "read" or arguments.get("content")):
            AuditLogger().log(tool="policy", arguments={"tool": name}, result="DENIED")
            return "ERROR: solo se permite lectura desde el modelo."
        fields = tool.parameters["properties"]
        for field, value in arguments.items():
            if field not in fields or (fields[field].get("type") == "string" and not isinstance(value, str)):
                return "ERROR: argumentos inválidos."
        return tool.execute(*args, **kwargs)


    def available_tools(self):

        return sorted(
            self.tools.keys()
        )


    def schemas(self):

        schemas = []
        for tool in self.tools.values():
            if self.permissions.requires_confirmation(tool.name):
                continue
            schema = tool.schema()
            if tool.name == "file":
                schema["function"]["description"] = "Lee un archivo UTF-8 del workspace."
                schema["function"]["parameters"] = {
                    "type": "object", "additionalProperties": False,
                    "properties": {"action": {"type": "string", "enum": ["read"]}, "path": {"type": "string"}},
                    "required": ["action", "path"],
                }
            schemas.append(schema)
        return schemas


    def tool_prompt(self):

        text = "Herramientas disponibles:\n\n"

        for tool in self.tools.values():
            if tool.name not in MODEL_TOOLS:
                continue

            text += (
                f"- {tool.name}: "
                f"{tool.description}\n"
            )

        return text
