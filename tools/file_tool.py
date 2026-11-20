"""
ARUS
File Tool

Fase 14: la clase `Sandbox` de aquí tenía un `validate(path)` que
SIEMPRE devolvía `True` -- un sandbox falso, sin ninguna comprobación
real (auditado y corregido, ver security/path_guard.py). Sustituido
por PathGuard, que sí restringe de verdad al área de trabajo. También
se añade auditoría real (antes esta tool no dejaba ningún rastro de
qué archivos tocaba).
"""

from tools.base_tool import BaseTool
from security.path_guard import PathGuard
from security.audit_logger import AuditLogger


class FileTool(BaseTool):
    name = "file"
    description = "Lee o escribe contenido de archivos dentro del área de trabajo de ARUS."
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "Acción: read o write"},
            "path": {"type": "string", "description": "Ruta del archivo"},
            "content": {"type": "string", "description": "Contenido para escribir (opcional)"}
        },
        "required": ["action", "path"]
    }

    def __init__(self, base_dir=None):
        self.guard = PathGuard(base_dir)
        self.audit = AuditLogger()

    def execute(self, action: str, path: str, content: str = ""):
        permitido, motivo = self.guard.validate(path)

        if not permitido:
            self.audit.log(tool="file", arguments={"action": action, "path": path}, result=motivo)
            return f"ERROR: {motivo}"

        if action == "read":
            try:
                resultado = self.guard.read(path)
            except (OSError, ValueError):
                resultado = "ERROR: No se pudo leer el archivo autorizado."
        elif action == "write":
            try:
                self.guard.write(path, content)
                resultado = "OK"
            except (OSError, ValueError):
                resultado = "ERROR: No se pudo escribir el archivo autorizado."
        else:
            resultado = "ERROR: Acción desconocida."

        self.audit.log(tool="file", arguments={"action": action, "path": path}, result="ERROR" if resultado.startswith("ERROR:") else "OK")
        return resultado
