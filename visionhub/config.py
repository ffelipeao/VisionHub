"""Carregamento e validação das configurações do VisionHub."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


def required_env(name: str) -> str:
    """Retorna uma variável obrigatória ou informa como configurá-la."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"A variável {name} não foi definida. "
            "Preencha o arquivo .env na pasta do projeto."
        )
    return value


def int_env(name: str, default: int | None = None) -> int:
    """Lê uma variável inteira e aceita um valor padrão opcional."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        if default is not None:
            return default
        raise RuntimeError(f"A variável {name} não foi definida no arquivo .env.")
    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"A variável {name} deve ser um número inteiro.") from error


def bool_env(name: str, default: bool = False) -> bool:
    """Lê uma variável booleana e informa valores inválidos claramente."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "on", "sim"}:
        return True
    if value in {"0", "false", "no", "off", "nao", "não"}:
        return False
    raise RuntimeError(
        f"A variável {name} deve ser 'true' ou 'false'."
    )


NVR_IP = required_env("NVR_IP")
NVR_RTSP_PORT = int_env("NVR_RTSP_PORT", 554)
NVR_USER = required_env("NVR_USER")
NVR_PASSWORD = required_env("NVR_PASSWORD")
NVR_STREAM = int_env("NVR_STREAM", 1)
CAMERA_COUNT = int_env("CAMERA_COUNT", 4)
SUPPRESS_CONNECTION_ERRORS = bool_env("SUPPRESS_CONNECTION_ERRORS", False)

if SUPPRESS_CONNECTION_ERRORS:
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")

WINDOW_WIDTH = int_env("WINDOW_WIDTH", 1280)
WINDOW_HEIGHT = int_env("WINDOW_HEIGHT", 720)
UI_FPS = int_env("UI_FPS", 15)
RECONNECT_SECONDS = float(os.getenv("RECONNECT_SECONDS", "3.0"))
RECONNECT_MAX_SECONDS = float(os.getenv("RECONNECT_MAX_SECONDS", "60.0"))
WINDOW_SCALE = float(os.getenv("WINDOW_SCALE", "0.92"))
IMAGE_FIT = os.getenv("IMAGE_FIT", "contain").strip().lower()
AUDIO_VOLUME = int_env("AUDIO_VOLUME", 50)
FFPLAY_PATH = shutil.which(os.getenv("FFPLAY_PATH", "ffplay"))

if IMAGE_FIT not in {"cover", "contain"}:
    raise RuntimeError("A variável IMAGE_FIT deve ser 'cover' ou 'contain'.")
if CAMERA_COUNT not in {4, 8}:
    raise RuntimeError("A variável CAMERA_COUNT deve ser 4 ou 8.")
if not 0 <= AUDIO_VOLUME <= 100:
    raise RuntimeError("A variável AUDIO_VOLUME deve estar entre 0 e 100.")


@dataclass(frozen=True)
class CameraConfig:
    """Identifica uma câmera e produz seu endereço RTSP."""

    name: str
    channel: int

    @property
    def url(self) -> str:
        """Monta a URL RTSP protegendo caracteres especiais das credenciais."""
        user = quote(NVR_USER, safe="")
        password = quote(NVR_PASSWORD, safe="")
        return (
            f"rtsp://{user}:{password}@{NVR_IP}:{NVR_RTSP_PORT}"
            f"/avstream/channel={self.channel}/stream={NVR_STREAM}.sdp"
        )


CAMERAS = [
    CameraConfig(
        os.getenv(f"CAMERA_{channel}_NAME", "").strip() or f"Câmera {channel}",
        channel,
    )
    for channel in range(1, CAMERA_COUNT + 1)
]
