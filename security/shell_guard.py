"""Parse only the built-in read-only operations exposed by ShellTool."""
import shlex


class ShellGuard:
    def parse(self, command):
        if not isinstance(command, str) or len(command) > 4096 or any(ord(c) < 32 for c in command):
            raise ValueError("Comando inválido")
        words = shlex.split(command)
        if not words:
            raise ValueError("Comando vacío")
        name, *args = words
        allowed = (name == "pwd" and not args or name == "echo"
                   or name == "ls" and len(args) <= 1 or name == "cat" and len(args) == 1)
        if not allowed:
            raise ValueError("Operación bloqueada por seguridad")
        return name, args

    def allowed(self, command):
        try:
            self.parse(command)
            return True
        except ValueError:
            return False
