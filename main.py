#!/usr/bin/env python3
"""
VigiaGrid — reprodutor de câmeras RTSP em mosaico 2x2.

Requisitos:
    python3 -m pip install -r requirements.txt

Antes de executar, copie .env.example para .env e preencha os dados do NVR.
No NVR, deixe RTSP ativado na porta 554.
"""

from __future__ import annotations

import queue
import os
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote

# Uma câmera offline é uma condição esperada da aplicação. Evita que tentativas
# de conexão do backend sejam escritas repetidamente no terminal.
os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")

import cv2
from dotenv import load_dotenv
from PIL import Image, ImageTk


load_dotenv(Path(__file__).with_name(".env"))

# Usa TCP no RTSP para evitar perdas de pacotes e negociações instáveis via UDP.
# A opção é consultada pelo backend FFmpeg ao abrir cada VideoCapture.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


def required_env(name: str) -> str:
    """Lê uma variável obrigatória e falha com uma mensagem útil."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"A variável {name} não foi definida. "
            "Preencha o arquivo .env na pasta do projeto."
        )
    return value


def int_env(name: str, default: int | None = None) -> int:
    """Lê uma variável inteira, aceitando um valor padrão opcional."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        if default is not None:
            return default
        raise RuntimeError(f"A variável {name} não foi definida no arquivo .env.")
    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"A variável {name} deve ser um número inteiro.") from error


# =========================
# CONFIGURAÇÃO DO SEU NVR
# =========================
NVR_IP = required_env("NVR_IP")
NVR_RTSP_PORT = int_env("NVR_RTSP_PORT", 554)
NVR_USER = required_env("NVR_USER")
NVR_PASSWORD = required_env("NVR_PASSWORD")
NVR_STREAM = int_env("NVR_STREAM", 1)

# 0 = stream principal (melhor qualidade)
# 1 = substream (mais leve e recomendado para 4 câmeras via Wi-Fi)
LARGURA_JANELA = int_env("WINDOW_WIDTH", 1280)
ALTURA_JANELA = int_env("WINDOW_HEIGHT", 720)
FPS_INTERFACE = int_env("UI_FPS", 15)
TEMPO_RECONEXAO = float(os.getenv("RECONNECT_SECONDS", "3.0"))
TEMPO_RECONEXAO_MAXIMO = float(os.getenv("RECONNECT_MAX_SECONDS", "60.0"))

# Alguns NVRs retornam erro 500 quando vários canais fazem DESCRIBE ao mesmo tempo.
RTSP_CONNECTION_LOCK = threading.Lock()


@dataclass(frozen=True)
class CameraConfig:
    nome: str
    canal: int

    @property
    def url(self) -> str:
        # Evita que caracteres especiais nas credenciais quebrem a URL RTSP.
        user = quote(NVR_USER, safe="")
        password = quote(NVR_PASSWORD, safe="")
        return (
            f"rtsp://{user}:{password}@{NVR_IP}:{NVR_RTSP_PORT}"
            f"/avstream/channel={self.canal}/stream={NVR_STREAM}.sdp"
        )


CAMERAS = [
    CameraConfig("Câmera 1", 1),
    CameraConfig("Câmera 2", 2),
    CameraConfig("Câmera 3", 3),
    CameraConfig("Câmera 4", 4),
]


class CameraWorker(threading.Thread):
    """Lê uma câmera RTSP em segundo plano e mantém somente o quadro mais recente."""

    def __init__(self, config: CameraConfig) -> None:
        super().__init__(daemon=True)
        self.config = config
        self.frames: queue.Queue = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.status = "Conectando…"

    def stop(self) -> None:
        self.stop_event.set()

    def _publish(self, frame) -> None:
        try:
            self.frames.get_nowait()
        except queue.Empty:
            pass
        try:
            self.frames.put_nowait(frame)
        except queue.Full:
            pass

    def run(self) -> None:
        reconnect_delay = TEMPO_RECONEXAO

        while not self.stop_event.is_set():
            capture: Optional[cv2.VideoCapture] = None
            try:
                self.status = "Conectando…"

                # FFMPEG costuma ser o backend mais confiável para RTSP.
                # Serializa somente a negociação inicial. Depois de conectados,
                # todos os canais continuam lendo em paralelo normalmente.
                with RTSP_CONNECTION_LOCK:
                    # O FFmpeg escreve falhas RTSP diretamente no descritor 2,
                    # ignorando o nível de log do OpenCV. Suprime apenas essa
                    # curta abertura; o restante da aplicação não é afetado.
                    saved_stderr = os.dup(2)
                    null_stderr = os.open(os.devnull, os.O_WRONLY)
                    try:
                        os.dup2(null_stderr, 2)
                        capture = cv2.VideoCapture(
                            self.config.url,
                            cv2.CAP_FFMPEG,
                        )
                        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        opened = capture.isOpened()
                    finally:
                        os.dup2(saved_stderr, 2)
                        os.close(saved_stderr)
                        os.close(null_stderr)

                if not opened:
                    self.status = "Sem conexão"
                    self.stop_event.wait(reconnect_delay)
                    reconnect_delay = min(
                        reconnect_delay * 2,
                        TEMPO_RECONEXAO_MAXIMO,
                    )
                    continue

                self.status = "Online"
                reconnect_delay = TEMPO_RECONEXAO

                while not self.stop_event.is_set():
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        self.status = "Reconectando…"
                        break

                    # OpenCV fornece BGR; Pillow/Tkinter usam RGB.
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
                    TEMPO_RECONEXAO_MAXIMO,
                )


class CameraPanel(tk.Frame):
    def __init__(self, master, worker: CameraWorker) -> None:
        super().__init__(master, bg="black", highlightthickness=1, highlightbackground="#444")
        self.worker = worker
        self.photo: Optional[ImageTk.PhotoImage] = None

        self.video_label = tk.Label(self, bg="black")
        self.video_label.pack(fill="both", expand=True)

        self.title_label = tk.Label(
            self,
            text=worker.config.nome,
            bg="#111",
            fg="white",
            font=("Helvetica", 13, "bold"),
            anchor="w",
            padx=10,
            pady=5,
        )
        self.title_label.place(x=0, y=0, relwidth=1)

        self.status_label = tk.Label(
            self,
            text="Conectando…",
            bg="#111",
            fg="white",
            font=("Helvetica", 11),
            padx=8,
            pady=4,
        )
        self.status_label.place(relx=1, x=-8, y=5, anchor="ne")

    def refresh(self) -> None:
        self.status_label.config(text=self.worker.status)

        try:
            frame = self.worker.frames.get_nowait()
        except queue.Empty:
            return

        panel_w = max(self.video_label.winfo_width(), 320)
        panel_h = max(self.video_label.winfo_height(), 180)

        image = Image.fromarray(frame)
        image.thumbnail((panel_w, panel_h), Image.Resampling.LANCZOS)

        # Centraliza a imagem em um fundo preto sem distorcer a proporção.
        canvas = Image.new("RGB", (panel_w, panel_h), "black")
        x = (panel_w - image.width) // 2
        y = (panel_h - image.height) // 2
        canvas.paste(image, (x, y))

        self.photo = ImageTk.PhotoImage(canvas)
        self.video_label.configure(image=self.photo)


class MosaicApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.fullscreen = False

        root.title("VigiaGrid — 4 Câmeras")
        root.geometry(f"{LARGURA_JANELA}x{ALTURA_JANELA}")
        root.minsize(800, 500)
        root.configure(bg="black")

        self.workers = [CameraWorker(camera) for camera in CAMERAS]
        self.panels = [CameraPanel(root, worker) for worker in self.workers]

        for row in range(2):
            root.grid_rowconfigure(row, weight=1, uniform="row")
        for col in range(2):
            root.grid_columnconfigure(col, weight=1, uniform="col")

        for index, panel in enumerate(self.panels):
            row, col = divmod(index, 2)
            panel.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

        for worker in self.workers:
            worker.start()

        root.bind("<Escape>", self.exit_fullscreen)
        root.bind("<F11>", self.toggle_fullscreen)
        root.bind("<Command-f>", self.toggle_fullscreen)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.refresh()

    def refresh(self) -> None:
        for panel in self.panels:
            panel.refresh()
        delay_ms = max(1, int(1000 / FPS_INTERFACE))
        self.root.after(delay_ms, self.refresh)

    def toggle_fullscreen(self, _event=None) -> None:
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self, _event=None) -> None:
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)

    def close(self) -> None:
        for worker in self.workers:
            worker.stop()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    MosaicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
