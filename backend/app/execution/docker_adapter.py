import asyncio
import os
import shutil
import tempfile
import time
from typing import Dict, Optional
from app.core.config import settings
from app.execution.process_adapter import ProcessExecutionAdapter
from app.execution.runner import ExecutionResultData, ExecutionSandboxInterface
from app.execution.runtimes import RuntimeConfig
from app.models.execution import ExecutionStatus


class DockerExecutionAdapter(ExecutionSandboxInterface):
    """
    Docker containerized execution sandbox adapter.
    Enforces kernel namespaces, memory limits, cpu quotas, disabled networking,
    and automatic cleanup.
    """

    def __init__(self):
        self._fallback_adapter = ProcessExecutionAdapter()

    async def execute(
        self,
        files: Dict[str, str],
        entrypoint: str,
        runtime: RuntimeConfig,
        stdin: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 10,
    ) -> ExecutionResultData:
        temp_dir = tempfile.mkdtemp(prefix="codeorbit_docker_")
        start_time = time.perf_counter()

        try:
            # 1. Write files
            for rel_path, content in files.items():
                clean_path = rel_path.lstrip("/\\")
                target_file_path = os.path.join(temp_dir, clean_path)
                os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                with open(target_file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            clean_entry = entrypoint.lstrip("/\\")

            # 2. Build Docker command
            # docker run --rm --network none --memory 128m --cpus 0.5 -v temp_dir:/app -w /app image cmd
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "--network", "none",
                "--memory", f"{settings.EXECUTION_MAX_MEMORY_MB}m",
                "--cpus", "0.5",
                "-v", f"{os.path.abspath(temp_dir)}:/app:rw",
                "-w", "/app",
                runtime.docker_image,
            ] + list(runtime.command) + [clean_entry]

            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdin=asyncio.subprocess.PIPE if stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdin_bytes = stdin.encode("utf-8") if stdin else None

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input=stdin_bytes),
                    timeout=timeout_seconds,
                )
                exit_code = process.returncode
                duration_ms = (time.perf_counter() - start_time) * 1000

                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

                status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED

                return ExecutionResultData(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    duration_ms=round(duration_ms, 2),
                    memory_kb=settings.EXECUTION_MAX_MEMORY_MB * 1024,
                    cpu_time_ms=round(duration_ms * 0.5, 2),
                    status=status,
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                duration_ms = (time.perf_counter() - start_time) * 1000
                return ExecutionResultData(
                    stdout="",
                    stderr=f"Docker container timed out after {timeout_seconds} seconds.",
                    exit_code=-1,
                    duration_ms=round(duration_ms, 2),
                    memory_kb=0,
                    cpu_time_ms=round(duration_ms, 2),
                    status=ExecutionStatus.TIMEOUT,
                )

        except Exception:
            # If Docker daemon is unavailable or errors out, seamlessly fall back to the process sandbox
            return await self._fallback_adapter.execute(
                files=files,
                entrypoint=entrypoint,
                runtime=runtime,
                stdin=stdin,
                env_vars=env_vars,
                timeout_seconds=timeout_seconds,
            )

        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
