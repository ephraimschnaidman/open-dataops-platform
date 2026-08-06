from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections.abc import Sequence

from .models import CommandResult
from .timing import utc_timestamp


class CommandError(RuntimeError):
    def __init__(self, message: str, result: CommandResult | None = None):
        super().__init__(message)
        self.result = result


class CommandTimeoutError(CommandError):
    pass


def run_command(
    command: Sequence[str], timeout: float = 60.0, stream: bool = False,
    check: bool = True,
) -> CommandResult:
    args = [str(value) for value in command]
    if not args:
        raise ValueError("command must not be empty")
    started_at = utc_timestamp()
    started = time.monotonic()
    if stream:
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            shell=False, errors="replace", bufsize=1,
        )
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        def copy_output(source, destination, parts: list[str]) -> None:
            assert source is not None
            for line in iter(source.readline, ""):
                parts.append(line)
                destination.write(line)
                destination.flush()

        threads = [
            threading.Thread(target=copy_output, args=(process.stdout, sys.stdout, stdout_parts), daemon=True),
            threading.Thread(target=copy_output, args=(process.stderr, sys.stderr, stderr_parts), daemon=True),
        ]
        for thread in threads:
            thread.start()
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            for thread in threads:
                thread.join()
            result = CommandResult(args, -1, "".join(stdout_parts), "".join(stderr_parts),
                                   started_at, utc_timestamp(), time.monotonic() - started)
            raise CommandTimeoutError(f"Command timed out after {timeout:g}s: {args[0]}", result) from exc
        for thread in threads:
            thread.join()
        result = CommandResult(args, return_code, "".join(stdout_parts), "".join(stderr_parts),
                               started_at, utc_timestamp(), time.monotonic() - started)
        if check and result.return_code != 0:
            raise CommandError(f"Command failed with exit code {result.return_code}: {args[0]}", result)
        return result
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, shell=False,
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        result = CommandResult(args, -1, stdout, stderr, started_at, utc_timestamp(), duration)
        raise CommandTimeoutError(
            f"Command timed out after {timeout:g}s: {args[0]}", result
        ) from exc
    result = CommandResult(
        args, completed.returncode, completed.stdout, completed.stderr,
        started_at, utc_timestamp(), time.monotonic() - started,
    )
    if check and result.return_code != 0:
        raise CommandError(
            f"Command failed with exit code {result.return_code}: {args[0]}", result
        )
    return result
