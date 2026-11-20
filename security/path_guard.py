"""Shared workspace policy and bounded POSIX reads."""
from __future__ import annotations

from contextlib import contextmanager
import os
import secrets
from pathlib import Path
import stat

MAX_READ = 256 * 1024


class PathGuard:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or os.environ.get("ARUS_WORKSPACE") or Path.cwd()).resolve(strict=True)

    def _parts(self, path):
        if not isinstance(path, str) or not path or len(path) > 4096 or "\0" in path:
            raise ValueError("Ruta inválida")
        candidate = Path(path)
        if ".." in candidate.parts:
            raise ValueError("Acceso denegado: ruta fuera del área de trabajo")
        if candidate.is_absolute():
            candidate = candidate.relative_to(self.base_dir)
        if any(part.startswith(".") for part in candidate.parts):
            raise ValueError("La ruta contiene componentes ocultos")
        return candidate.parts

    def validate(self, path):
        try:
            candidate = self.base_dir.joinpath(*self._parts(path))
            candidate.resolve().relative_to(self.base_dir)
        except (ValueError, OSError, RuntimeError):
            return False, "Acceso denegado: ruta inválida o fuera del área de trabajo."
        return True, ""

    @contextmanager
    def _directory(self, parts, *, create=False):
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise OSError("Lectura aislada no disponible en este sistema")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open(self.base_dir, flags)
        try:
            for part in parts:
                try:
                    child = os.open(part, flags, dir_fd=descriptor)
                except FileNotFoundError:
                    if not create:
                        raise
                    try:
                        os.mkdir(part, 0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                    child = os.open(part, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            yield descriptor
        finally:
            os.close(descriptor)

    def read(self, path):
        parts = self._parts(path)
        if not parts:
            raise ValueError("Selecciona un archivo")
        with self._directory(parts[:-1]) as parent:
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, "rb") as file:
                info = os.fstat(file.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_READ:
                    raise ValueError("Archivo no permitido o demasiado grande")
                data = file.read(MAX_READ + 1)
        if len(data) > MAX_READ:
            raise ValueError("Archivo demasiado grande")
        return data.decode("utf-8")

    def list(self, path):
        with self._directory(self._parts(path)) as directory, os.scandir(directory) as entries:
            result = []
            for index, item in enumerate(entries):
                if index == 1000 or len(result) == 200:
                    return sorted(result) + ["(listado truncado)"]
                if not item.name.startswith("."):
                    result.append(item.name)
        return sorted(result)


    def write(self, path, content):
        parts = self._parts(path)
        if not parts or not isinstance(content, str) or len(content) > MAX_READ:
            raise ValueError("Archivo o tamaño inválido")
        data = content.encode("utf-8")
        if len(data) > MAX_READ:
            raise ValueError("Archivo demasiado grande")
        with self._directory(parts[:-1], create=True) as parent:
            name = parts[-1]
            mode = 0o600
            try:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError("Destino no permitido")
                mode = stat.S_IMODE(info.st_mode) & 0o777
            temporary = ".arus-" + secrets.token_hex(16)
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode, dir_fd=parent)
            try:
                with os.fdopen(fd, "wb") as file:
                    file.write(data)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
