"""Controle de instância única do VisionHub."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import BinaryIO


PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_PACKAGED = getattr(sys, "frozen", False)
RUNTIME_DIR = Path.home() / ".visionhub" if IS_PACKAGED else PROJECT_ROOT


class InstanceLock:
    """Mantém um bloqueio de arquivo enquanto a aplicação está aberta."""

    def __init__(self, handle: BinaryIO) -> None:
        self.handle = handle

    def release(self) -> None:
        """Libera o bloqueio e fecha seu descritor."""
        if self.handle.closed:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()


def acquire_instance_lock() -> InstanceLock | None:
    """Obtém a trava exclusiva ou informa que outra instância está ativa."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    handle = (RUNTIME_DIR / "visionhub.lock").open("a+b")
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)

    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return InstanceLock(handle)
