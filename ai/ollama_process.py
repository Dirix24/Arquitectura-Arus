"""Manage only the Ollama process started by this ARUS instance."""
import os
import shutil
import socket
import subprocess
from urllib.parse import urlsplit


class OllamaProcess:
    def __init__(self):
        self.process = None

    def start(self, endpoint="http://127.0.0.1:11434"):
        url = urlsplit(endpoint)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "::1", "localhost"}
            or url.username or url.password or url.path not in ("", "/") or url.query or url.fragment):
            raise ValueError("Inicio automático de Ollama limitado a loopback")
        if self.process is not None and self.process.poll() is None:
            return "owned"
        self.process = None
        host = "127.0.0.1" if url.hostname == "localhost" else url.hostname
        port = url.port or 11434
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return "existing"
        except ConnectionRefusedError:
            pass
        except OSError as exc:
            raise RuntimeError("No se pudo determinar el estado del puerto de Ollama") from exc

        binary = os.environ.get("ARUS_OLLAMA_PATH") or shutil.which("ollama") or "ollama"
        address = f"[{host}]" if ":" in host else host
        env = {
            **os.environ, "OLLAMA_HOST": f"{address}:{port}", "OLLAMA_NUM_PARALLEL": "1",
            "OLLAMA_VULKAN": "0", "CUDA_VISIBLE_DEVICES": "",
        }
        self.process = subprocess.Popen(
            [binary, "serve"], env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=os.name == "posix",
        )
        return "started"

    def stop(self):
        process = self.process
        self.process = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("Ollama no terminó tras la señal de cierre") from exc
        except ProcessLookupError:
            pass
