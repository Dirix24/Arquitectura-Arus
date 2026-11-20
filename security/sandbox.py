"""Legacy adapter for the shared filesystem path policy."""
from .path_guard import PathGuard


class Sandbox:
    def __init__(self, base_dir=None):
        self.guard = PathGuard(base_dir)

    def check(self, path):
        return self.guard.validate(path)[0]
