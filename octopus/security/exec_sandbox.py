"""Execution sandbox — three isolation levels for running shell commands."""

from __future__ import annotations

import shlex
import subprocess
from abc import ABC, abstractmethod
from typing import Any


class ExecResult:
    def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.ok = returncode == 0

    def to_dict(self) -> dict[str, Any]:
        return {"stdout": self.stdout, "stderr": self.stderr, "returncode": self.returncode}


class BaseExecutor(ABC):
    @abstractmethod
    def run(self, command: str, timeout: int = 30) -> ExecResult:
        ...


class DockerExecutor(BaseExecutor):
    """Runs commands inside a throw-away Docker container."""

    def __init__(self, image: str = "python:3.11-slim", memory: str = "256m", cpus: str = "0.5") -> None:
        self._image = image
        self._memory = memory
        self._cpus = cpus

    def run(self, command: str, timeout: int = 30) -> ExecResult:
        docker_cmd = [
            "docker", "run", "--rm",
            "--network=none",
            f"--memory={self._memory}",
            f"--cpus={self._cpus}",
            "--security-opt=no-new-privileges",
            self._image,
            "sh", "-c", command,
        ]
        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecResult(proc.stdout, proc.stderr, proc.returncode)
        except subprocess.TimeoutExpired:
            return ExecResult("", f"Command timed out after {timeout}s", 124)
        except FileNotFoundError:
            return ExecResult("", "Docker is not installed or not in PATH", 127)


class SandboxExecExecutor(BaseExecutor):
    """Runs commands under macOS sandbox-exec with a deny-default profile."""

    # Allows reading most of the filesystem and executing processes,
    # but denies all network access and writes outside /tmp.
    _PROFILE = """
(version 1)
(deny default)
(allow process-exec)
(allow process-fork)
(allow file-read*)
(allow file-write* (subpath "/tmp"))
(allow file-write* (subpath "/private/tmp"))
(allow sysctl-read)
(allow mach-lookup)
(allow signal (target self))
"""

    def run(self, command: str, timeout: int = 30) -> ExecResult:
        cmd = ["sandbox-exec", "-p", self._PROFILE, "sh", "-c", command]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecResult(proc.stdout, proc.stderr, proc.returncode)
        except subprocess.TimeoutExpired:
            return ExecResult("", f"Command timed out after {timeout}s", 124)
        except FileNotFoundError:
            return ExecResult("", "sandbox-exec not available (macOS only)", 127)


class UnsafeExecutor(BaseExecutor):
    """Runs commands directly — no isolation whatsoever. Use deliberately."""

    def run(self, command: str, timeout: int = 30) -> ExecResult:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecResult(proc.stdout, proc.stderr, proc.returncode)
        except subprocess.TimeoutExpired:
            return ExecResult("", f"Command timed out after {timeout}s", 124)


def build_executor(driver: str, **kwargs) -> BaseExecutor:
    """Factory — driver is 'docker', 'sandbox-exec', or 'none'."""
    if driver == "docker":
        return DockerExecutor(**kwargs)
    if driver == "sandbox-exec":
        return SandboxExecExecutor()
    if driver == "none":
        return UnsafeExecutor()
    raise ValueError(f"Unknown exec_sandbox driver: {driver!r}. Choose: docker, sandbox-exec, none")
