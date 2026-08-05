"""Leitura de vídeo e reprodução de áudio RTSP do VisionHub."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
from typing import Optional

from .config import (
    AUDIO_VOLUME,
    FFPLAY_PATH,
    RECONNECT_MAX_SECONDS,
    RECONNECT_SECONDS,
    SUPPRESS_CONNECTION_ERRORS,
    CameraConfig,
)

# A configuração precisa ser importada antes do OpenCV para aplicar o nível de
# log e as opções do backend FFmpeg.
import cv2


RTSP_CONNECTION_LOCK = threading.Lock()


class CameraWorker(threading.Thread):
    """Lê uma câmera em segundo plano e conserva apenas o quadro mais recente."""

    def __init__(self, config: CameraConfig) -> None:
        """Prepara a thread e o buffer de um único quadro da câmera."""
        super().__init__(daemon=True)
        self.config = config
        self.frames: queue.Queue = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.status = "Conectando…"

    def stop(self) -> None:
        """Solicita o encerramento da leitura sem bloquear a interface."""
        self.stop_event.set()

    def _publish(self, frame) -> None:
        """Substitui o quadro anterior para evitar atraso acumulado no vídeo."""
        try:
            self.frames.get_nowait()
        except queue.Empty:
            pass
        try:
            self.frames.put_nowait(frame)
        except queue.Full:
            pass

    def _open_capture(self) -> cv2.VideoCapture:
        """Abre o RTSP e aplica a configuração de mensagens de conexão."""
        with RTSP_CONNECTION_LOCK:
            if not SUPPRESS_CONNECTION_ERRORS:
                capture = cv2.VideoCapture(self.config.url, cv2.CAP_FFMPEG)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return capture

            saved_stderr = os.dup(2)
            null_stderr = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(null_stderr, 2)
                capture = cv2.VideoCapture(self.config.url, cv2.CAP_FFMPEG)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return capture
            finally:
                os.dup2(saved_stderr, 2)
                os.close(saved_stderr)
                os.close(null_stderr)

    def run(self) -> None:
        """Mantém a leitura ativa e aplica espera progressiva nas reconexões."""
        reconnect_delay = RECONNECT_SECONDS

        while not self.stop_event.is_set():
            capture: Optional[cv2.VideoCapture] = None
            try:
                self.status = "Conectando…"
                capture = self._open_capture()

                if not capture.isOpened():
                    self.status = "Sem conexão"
                    self.stop_event.wait(reconnect_delay)
                    reconnect_delay = min(
                        reconnect_delay * 2,
                        RECONNECT_MAX_SECONDS,
                    )
                    continue

                self.status = "Online"
                reconnect_delay = RECONNECT_SECONDS

                while not self.stop_event.is_set():
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        self.status = "Reconectando…"
                        break
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self._publish(frame)
            except Exception:
                self.status = "Erro — reconectando…"
            finally:
                if capture is not None:
                    capture.release()

            if not self.stop_event.is_set():
                self.stop_event.wait(reconnect_delay)
                reconnect_delay = min(
                    reconnect_delay * 2,
                    RECONNECT_MAX_SECONDS,
                )


class AudioController:
    """Reproduz o áudio RTSP de uma câmera por vez por meio do ffplay."""

    def __init__(self) -> None:
        """Inicializa o controlador sem reproduzir áudio automaticamente."""
        self.process: Optional[subprocess.Popen] = None
        self.active_camera: Optional[CameraConfig] = None
        self.volume = AUDIO_VOLUME

    @property
    def available(self) -> bool:
        """Informa se o executável ffplay foi localizado no sistema."""
        return FFPLAY_PATH is not None

    @property
    def playing(self) -> bool:
        """Informa se o processo de áudio continua ativo."""
        return self.process is not None and self.process.poll() is None

    def play(self, camera: CameraConfig, volume: int) -> bool:
        """Interrompe o áudio anterior e reproduz a câmera indicada."""
        self.stop()
        if FFPLAY_PATH is None:
            return False

        self.volume = max(0, min(100, int(volume)))
        self.process = subprocess.Popen(
            [
                FFPLAY_PATH,
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "quiet",
                "-rtsp_transport",
                "tcp",
                "-volume",
                str(self.volume),
                camera.url,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.active_camera = camera
        return True

    def set_volume(self, volume: int) -> None:
        """Reinicia somente o áudio ativo para aplicar o novo volume."""
        camera = self.active_camera
        if camera is not None:
            self.play(camera, volume)
        else:
            self.volume = max(0, min(100, int(volume)))

    def stop(self) -> None:
        """Encerra o ffplay e libera o processo sem deixá-lo órfão."""
        process = self.process
        self.process = None
        self.active_camera = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=0.5)
