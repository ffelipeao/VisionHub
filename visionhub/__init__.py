"""Componentes do reprodutor de câmeras RTSP VisionHub."""

from __future__ import annotations

__all__ = ["VisionHubApp"]


def __getattr__(name: str):
    """Carrega a aplicação sob demanda para permitir o primeiro acesso."""
    if name == "VisionHubApp":
        from .app import VisionHubApp

        return VisionHubApp
    raise AttributeError(name)
