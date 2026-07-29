"""Package shim that preserves Python's standard-library ``platform`` API.

The repository's established top-level directory is named ``platform``. Making
it importable for administrative module commands would otherwise shadow the
standard-library module of the same name, which dependencies such as Argon2
use. Execute that module in this package namespace so both APIs remain
available.
"""

from __future__ import annotations

import os

_stdlib_platform_path = os.path.join(
    os.path.dirname(os.__file__),
    "platform.py",
)
with open(_stdlib_platform_path, "rb") as _stdlib_platform_file:
    exec(
        compile(
            _stdlib_platform_file.read(),
            _stdlib_platform_path,
            "exec",
        ),
        globals(),
        globals(),
    )

del _stdlib_platform_file
del _stdlib_platform_path
