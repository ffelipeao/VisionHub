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
from typing import Callable, Optional
from urllib.parse import quote

# Uma câmera offline é uma condição esperada da aplicação. Evita que tentativas
# de conexão do backend sejam escritas repetidamente no terminal.
os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")

import cv2
from dotenv import load_dotenv
from PIL import Image, ImageOps, ImageTk


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
ESCALA_JANELA = float(os.getenv("WINDOW_SCALE", "0.92"))
AJUSTE_IMAGEM = os.getenv("IMAGE_FIT", "cover").strip().lower()

if AJUSTE_IMAGEM not in {"cover", "contain"}:
    raise RuntimeError("A variável IMAGE_FIT deve ser 'cover' ou 'contain'.")

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
    def __init__(
        self,
        master,
        worker: CameraWorker,
        on_expand: Callable[[], None],
        on_fullscreen: Callable[[], None],
    ) -> None:
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
        self.status_label.place(relx=1, x=-82, y=5, anchor="ne")

        self.fullscreen_button = tk.Button(
            self,
            text="⛶",
            command=on_fullscreen,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Helvetica", 16),
            cursor="hand2",
            padx=5,
            pady=0,
        )
        self.fullscreen_button.place(relx=1, x=-8, y=5, anchor="ne", width=32, height=28)

        self.expand_button = tk.Button(
            self,
            text="□",
            command=on_expand,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Helvetica", 17),
            cursor="hand2",
            padx=5,
            pady=0,
        )
        self.expand_button.place(relx=1, x=-43, y=5, anchor="ne", width=32, height=28)

    def refresh(self) -> None:
        self.status_label.config(text=self.worker.status)

        try:
            frame = self.worker.frames.get_nowait()
        except queue.Empty:
            return

        panel_w = max(self.video_label.winfo_width(), 320)
        panel_h = max(self.video_label.winfo_height(), 180)

        image = Image.fromarray(frame)
        if AJUSTE_IMAGEM == "cover":
            # Preenche todo o painel sem deformar; recorta apenas as bordas que
            # excedem a proporção disponível.
            canvas = ImageOps.fit(
                image,
                (panel_w, panel_h),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
        else:
            # Exibe o quadro inteiro e completa o espaço restante com preto.
            image.thumbnail((panel_w, panel_h), Image.Resampling.LANCZOS)
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
        self.expanded_panel: Optional[CameraPanel] = None
        self.panel_before_fullscreen: Optional[CameraPanel] = None
        self.geometry_before_fullscreen: Optional[str] = None

        root.title("VigiaGrid — 4 Câmeras")
        self.configure_initial_geometry()
        root.minsize(800, 500)
        root.configure(bg="black")

        self.workers = [CameraWorker(camera) for camera in CAMERAS]
        self.panels: list[CameraPanel] = []
        for worker in self.workers:
            panel: CameraPanel
            panel = CameraPanel(
                root,
                worker,
                on_expand=lambda: None,
                on_fullscreen=self.toggle_fullscreen,
            )
            panel.expand_button.config(
                command=lambda selected=panel: self.toggle_camera(selected)
            )
            panel.fullscreen_button.config(
                command=lambda selected=panel: self.toggle_panel_fullscreen(selected)
            )
            self.panels.append(panel)

        for row in range(2):
            root.grid_rowconfigure(row, weight=1, uniform="row")
        for col in range(2):
            root.grid_columnconfigure(col, weight=1, uniform="col")

        for index, panel in enumerate(self.panels):
            row, col = divmod(index, 2)
            panel.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
            for widget in (panel, panel.video_label, panel.title_label, panel.status_label):
                widget.bind(
                    "<Double-Button-1>",
                    lambda _event, selected=panel: self.toggle_camera(selected),
                )

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

    def configure_initial_geometry(self) -> None:
        """Dimensiona e centraliza a janela conforme a tela disponível."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        scale = min(max(ESCALA_JANELA, 0.5), 1.0)
        available_width = int(screen_width * scale)
        available_height = int(screen_height * scale)

        # Mantém a proporção configurada, aproveitando o máximo possível da tela.
        aspect_ratio = LARGURA_JANELA / max(ALTURA_JANELA, 1)
        width = available_width
        height = int(width / aspect_ratio)
        if height > available_height:
            height = available_height
            width = int(height * aspect_ratio)

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def toggle_fullscreen(self, _event=None) -> None:
        """Alterna tela cheia preservando a visualização atual."""
        if self.fullscreen:
            self.leave_fullscreen()
        else:
            self.enter_fullscreen()

    def toggle_panel_fullscreen(self, panel: CameraPanel) -> None:
        """Abre a câmera escolhida em tela cheia ou restaura a tela anterior."""
        if self.fullscreen:
            self.leave_fullscreen()
        else:
            self.enter_fullscreen(panel)

    def enter_fullscreen(self, panel: Optional[CameraPanel] = None) -> None:
        # Guarda tamanho e posição antes que o gerenciador de janelas altere a
        # geometria ao entrar em tela cheia.
        self.root.update_idletasks()
        self.geometry_before_fullscreen = self.root.geometry()
        self.panel_before_fullscreen = self.expanded_panel
        if panel is not None:
            self.show_camera(panel)

        self.fullscreen = True
        self.root.attributes("-fullscreen", True)
        for camera_panel in self.panels:
            camera_panel.fullscreen_button.config(text="↙")

    def leave_fullscreen(self) -> None:
        saved_geometry = self.geometry_before_fullscreen
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)

        if self.panel_before_fullscreen is None:
            self.show_mosaic()
        else:
            self.show_camera(self.panel_before_fullscreen)

        self.panel_before_fullscreen = None
        self.geometry_before_fullscreen = None
        for panel in self.panels:
            panel.fullscreen_button.config(text="⛶")

        if saved_geometry is not None:
            # Tk precisa concluir a saída da tela cheia antes de aceitar a
            # geometria anterior, especialmente no macOS.
            self.root.after(
                50,
                lambda geometry=saved_geometry: self.restore_geometry(geometry),
            )

    def restore_geometry(self, geometry: str) -> None:
        """Restaura a janela e força o recálculo dos quatro painéis."""
        self.root.geometry(geometry)
        self.root.update_idletasks()
        for panel in self.panels:
            panel.video_label.update_idletasks()

    def exit_fullscreen(self, _event=None) -> None:
        if self.fullscreen:
            self.leave_fullscreen()
        elif self.expanded_panel is not None:
            self.show_mosaic()

    def toggle_camera(self, panel: CameraPanel) -> None:
        """Alterna uma câmera entre a visualização ampliada e o mosaico."""
        if self.expanded_panel is panel:
            self.show_mosaic()
        else:
            self.show_camera(panel)

    def show_camera(self, selected_panel: CameraPanel) -> None:
        """Faz uma única câmera preencher toda a área do programa."""
        for panel in self.panels:
            panel.grid_remove()

        selected_panel.grid(
            row=0,
            column=0,
            rowspan=2,
            columnspan=2,
            sticky="nsew",
            padx=0,
            pady=0,
        )
        selected_panel.expand_button.config(text="▦")
        self.expanded_panel = selected_panel

    def show_mosaic(self) -> None:
        """Restaura as quatro câmeras na grade 2x2."""
        for panel in self.panels:
            panel.grid_remove()

        for index, panel in enumerate(self.panels):
            row, col = divmod(index, 2)
            panel.grid(
                row=row,
                column=col,
                rowspan=1,
                columnspan=1,
                sticky="nsew",
                padx=1,
                pady=1,
            )
            panel.expand_button.config(text="□")

        self.expanded_panel = None
        self.root.update_idletasks()

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
