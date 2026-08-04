"""Componentes visuais reutilizáveis da interface do VisionHub."""

from __future__ import annotations

import queue
import tkinter as tk
from typing import Callable, Optional

from PIL import Image, ImageOps, ImageTk

from .config import AUDIO_VOLUME, IMAGE_FIT
from .media import CameraWorker


BUTTON_COLOR = "#2563eb"
BUTTON_HOVER_COLOR = "#1d4ed8"
ICON_COLOR = "white"


class IconButton(tk.Canvas):
    """Exibe um botão vetorial consistente entre fontes e sistemas operacionais."""

    def __init__(
        self,
        master,
        icon: str,
        command: Callable[[], None],
    ) -> None:
        """Cria o canvas, registra interações e desenha o ícone inicial."""
        super().__init__(
            master,
            width=32,
            height=28,
            bg=BUTTON_COLOR,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
            takefocus=True,
        )
        self.icon = icon
        self.command = command
        self.bind("<Button-1>", self._activate)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._draw()

    def _activate(self, _event=None) -> None:
        """Executa a ação do botão por mouse ou teclado."""
        self.command()

    def _on_enter(self, _event=None) -> None:
        """Destaca o botão enquanto o ponteiro estiver sobre ele."""
        self._draw(BUTTON_HOVER_COLOR)

    def _on_leave(self, _event=None) -> None:
        """Restaura a cor normal quando o ponteiro deixa o botão."""
        self._draw(BUTTON_COLOR)

    def set_command(self, command: Callable[[], None]) -> None:
        """Substitui a ação executada ao ativar o botão."""
        self.command = command

    def set_icon(self, icon: str) -> None:
        """Troca o símbolo vetorial para refletir o estado atual."""
        self.icon = icon
        self._draw()

    def _draw(self, background: str = BUTTON_COLOR) -> None:
        """Limpa o canvas e encaminha o desenho ao ícone selecionado."""
        self.configure(bg=background)
        self.delete("icon")
        if self.icon in {"expand", "fullscreen"}:
            self._draw_expand(self.icon == "fullscreen")
        elif self.icon == "mosaic":
            self._draw_mosaic()
        elif self.icon == "restore":
            self._draw_restore()
        elif self.icon in {"audio_off", "audio_on"}:
            self._draw_audio(self.icon == "audio_on")

    def _draw_expand(self, fullscreen: bool) -> None:
        """Desenha quatro cantos e diferencia o modo de tela cheia."""
        segments = (
            (7, 11, 7, 7, 11, 7),
            (21, 7, 25, 7, 25, 11),
            (7, 17, 7, 21, 11, 21),
            (21, 21, 25, 21, 25, 17),
        )
        for segment in segments:
            self.create_line(*segment, fill=ICON_COLOR, width=2, tags="icon")
        if fullscreen:
            self.create_rectangle(
                11,
                10,
                21,
                18,
                outline=ICON_COLOR,
                width=1,
                tags="icon",
            )

    def _draw_mosaic(self) -> None:
        """Desenha quatro quadros que representam o mosaico 2x2."""
        for x, y in ((8, 7), (17, 7), (8, 15), (17, 15)):
            self.create_rectangle(
                x,
                y,
                x + 7,
                y + 6,
                outline=ICON_COLOR,
                width=2,
                tags="icon",
            )

    def _draw_restore(self) -> None:
        """Desenha duas janelas sobrepostas para indicar restauração."""
        self.create_rectangle(
            8,
            9,
            21,
            20,
            outline=ICON_COLOR,
            width=2,
            tags="icon",
        )
        self.create_line(
            12,
            9,
            12,
            6,
            25,
            6,
            25,
            17,
            21,
            17,
            fill=ICON_COLOR,
            width=2,
            tags="icon",
        )

    def _draw_audio(self, enabled: bool) -> None:
        """Desenha o alto-falante com ondas ou com um indicador de mudo."""
        self.create_polygon(
            7,
            12,
            12,
            12,
            18,
            7,
            18,
            21,
            12,
            16,
            7,
            16,
            fill=ICON_COLOR,
            outline=ICON_COLOR,
            tags="icon",
        )
        if enabled:
            self.create_arc(
                15,
                9,
                25,
                19,
                start=-55,
                extent=110,
                style="arc",
                outline=ICON_COLOR,
                width=2,
                tags="icon",
            )
            return
        self.create_line(
            21,
            10,
            27,
            18,
            fill=ICON_COLOR,
            width=2,
            tags="icon",
        )
        self.create_line(
            27,
            10,
            21,
            18,
            fill=ICON_COLOR,
            width=2,
            tags="icon",
        )


class CameraPanel(tk.Frame):
    """Agrupa vídeo, estado e controles de uma câmera."""

    def __init__(
        self,
        master,
        worker: CameraWorker,
        on_expand: Callable[[], None],
        on_fullscreen: Callable[[], None],
        on_audio: Callable[[], None],
        on_volume: Callable[[int], None],
    ) -> None:
        """Monta o painel e conecta seus controles às ações da aplicação."""
        super().__init__(
            master,
            bg="black",
            highlightthickness=1,
            highlightbackground="#444",
        )
        self.worker = worker
        self.photo: Optional[ImageTk.PhotoImage] = None

        self.video_label = tk.Label(self, bg="black")
        self.video_label.pack(fill="both", expand=True)

        self.title_label = tk.Label(
            self,
            text=worker.config.name,
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
        self.status_label.place(relx=1, x=-225, y=5, anchor="ne")

        self.fullscreen_button = IconButton(self, "fullscreen", on_fullscreen)
        self.fullscreen_button.place(
            relx=1, x=-8, y=5, anchor="ne", width=32, height=28
        )

        self.expand_button = IconButton(self, "expand", on_expand)
        self.expand_button.place(relx=1, x=-43, y=5, anchor="ne", width=32, height=28)

        self.audio_button = IconButton(self, "audio_off", on_audio)
        self.audio_button.place(relx=1, x=-78, y=5, anchor="ne", width=32, height=28)

        self.volume_scale = tk.Scale(
            self,
            from_=0,
            to=100,
            orient="horizontal",
            showvalue=False,
            command=lambda value: on_volume(int(float(value))),
            bg="#111",
            fg="white",
            activebackground=BUTTON_COLOR,
            troughcolor="#374151",
            highlightthickness=0,
            borderwidth=0,
            sliderlength=14,
        )
        self.volume_scale.set(AUDIO_VOLUME)
        self.volume_scale.place(
            relx=1,
            x=-115,
            y=5,
            anchor="ne",
            width=100,
            height=28,
        )

    def refresh(self) -> None:
        """Atualiza o estado e renderiza o quadro mais recente da câmera."""
        self.status_label.config(text=self.worker.status)
        try:
            frame = self.worker.frames.get_nowait()
        except queue.Empty:
            return

        panel_width = max(self.video_label.winfo_width(), 320)
        panel_height = max(self.video_label.winfo_height(), 180)
        canvas = self._resize_frame(frame, panel_width, panel_height)
        self.photo = ImageTk.PhotoImage(canvas)
        self.video_label.configure(image=self.photo)

    def _resize_frame(self, frame, width: int, height: int) -> Image.Image:
        """Ajusta o quadro ao painel usando recorte ou bordas sem deformação."""
        image = Image.fromarray(frame)
        if IMAGE_FIT == "cover":
            return ImageOps.fit(
                image,
                (width, height),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )

        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height), "black")
        x = (width - image.width) // 2
        y = (height - image.height) // 2
        canvas.paste(image, (x, y))
        return canvas
