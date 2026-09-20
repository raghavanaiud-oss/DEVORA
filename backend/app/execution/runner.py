import abc
import time
from dataclasses import dataclass
from typing import Dict, Optional
from app.core.config import settings
from app.execution.runtimes import RuntimeConfig, detect_runtime
from app.models.execution import ExecutionStatus


@dataclass
class ExecutionResultData:
    stdout: str
    stderr: str
    exit_code: Optional[int]
    duration_ms: float
    memory_kb: int
    cpu_time_ms: float
    status: ExecutionStatus


class ExecutionSandboxInterface(abc.ABC):
    @abc.abstractmethod
    async def execute(
        self,
        files: Dict[str, str],  # relative_path -> content
        entrypoint: str,
        runtime: RuntimeConfig,
        stdin: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 10,
    ) -> ExecutionResultData:
        pass


class ExecutionManager:
    def __init__(self):
        self._docker_adapter = None
        self._process_adapter = None

    def get_adapter(self) -> ExecutionSandboxInterface:
        if settings.EXECUTION_SANDBOX_TYPE == "docker":
            if self._docker_adapter is None:
                from app.execution.docker_adapter import DockerExecutionAdapter
                self._docker_adapter = DockerExecutionAdapter()
            return self._docker_adapter
        else:
            if self._process_adapter is None:
                from app.execution.process_adapter import ProcessExecutionAdapter
                self._process_adapter = ProcessExecutionAdapter()
            return self._process_adapter

    async def run_code(
        self,
        files: Dict[str, str],
        entrypoint: str,
        language: Optional[str] = None,
        stdin: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResultData:
        runtime = detect_runtime(entrypoint, language)
        adapter = self.get_adapter()
        return await adapter.execute(
            files=files,
            entrypoint=entrypoint,
            runtime=runtime,
            stdin=stdin,
            env_vars=env_vars,
            timeout_seconds=settings.EXECUTION_TIMEOUT_SECONDS,
        )


execution_manager = ExecutionManager()
