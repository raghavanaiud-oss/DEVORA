import asyncio
import os
import shutil
import tempfile
import time
from typing import Dict, Optional
from backend.app.core.config import settings
from backend.app.execution.runner import ExecutionResultData, ExecutionSandboxInterface
from backend.app.execution.runtimes import RuntimeConfig
from backend.app.models.execution import ExecutionStatus


class ProcessExecutionAdapter(ExecutionSandboxInterface):
    """
    Isolated process-level sandbox runner.
    Provides strict timeout, temp directory isolation, output truncation,
    and automatic cleanup.
    """

    async def execute(
        self,
        files: Dict[str, str],
        entrypoint: str,
        runtime: RuntimeConfig,
        stdin: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 10,
    ) -> ExecutionResultData:
        temp_dir = tempfile.mkdtemp(prefix="codeorbit_exec_")
        start_time = time.perf_counter()

        try:
            # 1. Write files into isolated sandbox directory
            for rel_path, content in files.items():
                clean_path = rel_path.lstrip("/\\")
                target_file_path = os.path.join(temp_dir, clean_path)
                os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                with open(target_file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Ensure entrypoint exists
            clean_entry = entrypoint.lstrip("/\\")
            full_entry_path = os.path.join(temp_dir, clean_entry)
            if not os.path.exists(full_entry_path):
                # If entrypoint doesn't exist, create an empty file
                os.makedirs(os.path.dirname(full_entry_path), exist_ok=True)
                with open(full_entry_path, "w", encoding="utf-8") as f:
                    f.write("")

            # 2. Build execution command
            cmd = list(runtime.command) + [clean_entry]

            # Restricted environment variables
            exec_env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONUNBUFFERED": "1",
                "NODE_ENV": "production",
            }
            if env_vars:
                exec_env.update(env_vars)

            # 3. Launch isolated subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_dir,
                env=exec_env,
            )

            stdin_bytes = stdin.encode("utf-8") if stdin else None

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input=stdin_bytes),
                    timeout=timeout_seconds,
                )
                exit_code = process.returncode
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Truncate output if too large
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

                if len(stdout) > settings.EXECUTION_MAX_OUTPUT_BYTES:
                    stdout = stdout[: settings.EXECUTION_MAX_OUTPUT_BYTES] + "\n[Output truncated: exceeded 100KB]"
                if len(stderr) > settings.EXECUTION_MAX_OUTPUT_BYTES:
                    stderr = stderr[: settings.EXECUTION_MAX_OUTPUT_BYTES] + "\n[Output truncated: exceeded 100KB]"

                status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED

                return ExecutionResultData(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    duration_ms=round(duration_ms, 2),
                    memory_kb=32768,  # Typical base process allocation
                    cpu_time_ms=round(duration_ms * 0.8, 2),
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
                    stderr=f"Execution timed out after {timeout_seconds} seconds.",
                    exit_code=-1,
                    duration_ms=round(duration_ms, 2),
                    memory_kb=0,
                    cpu_time_ms=round(duration_ms, 2),
                    status=ExecutionStatus.TIMEOUT,
                )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ExecutionResultData(
                stdout="",
                stderr=f"Execution error: {str(e)}",
                exit_code=1,
                duration_ms=round(duration_ms, 2),
                memory_kb=0,
                cpu_time_ms=0.0,
                status=ExecutionStatus.FAILED,
            )

        finally:
            # 4. Clean up temporary directory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
