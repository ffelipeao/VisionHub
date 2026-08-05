"""Coordenação da janela, dos painéis e das interações do VisionHub."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from .config import (
    CAMERAS,
    UI_FPS,
    WINDOW_HEIGHT,
    WINDOW_SCALE,
    WINDOW_WIDTH,
)
from .media import AudioController, CameraWorker
from .version import __version__
from .widgets import CameraPanel


class VisionHubApp:
    """Controla o ciclo de vida e os modos de visualização da aplicação."""

    def __init__(self, root: tk.Tk) -> None:
        """Configura a janela, cria os painéis e inicia os leitores de vídeo."""
        self.root = root
        self.fullscreen = False
        self.expanded_panel: Optional[CameraPanel] = None
        self.panel_before_fullscreen: Optional[CameraPanel] = None
        self.geometry_before_fullscreen: Optional[str] = None
        self.audio = AudioController()
        self.active_audio_panel: Optional[CameraPanel] = None
        self.volume_update_id: Optional[str] = None

        root.title(
            f"VisionHub {__version__} — {len(CAMERAS)} Câmeras"
        )
        self.configure_initial_geometry()
        root.minsize(max(800, (len(CAMERAS) // 2) * 280), 500)
        root.configure(bg="black")

        self.workers = [CameraWorker(camera) for camera in CAMERAS]
        self.panels = [self._create_panel(worker) for worker in self.workers]
        self.grid_rows = 2
        self.grid_columns = len(self.panels) // self.grid_rows
        self._configure_grid()
        self._bind_window_events()

        for worker in self.workers:
            worker.start()
        self.refresh()

    def _create_panel(self, worker: CameraWorker) -> CameraPanel:
        """Cria um painel e conecta ações que dependem da própria instância."""
        panel = CameraPanel(
            self.root,
            worker,
            on_expand=lambda: None,
            on_fullscreen=lambda: None,
            on_audio=lambda: None,
            on_volume=lambda _volume: None,
        )
        panel.expand_button.set_command(
            lambda selected=panel: self.toggle_camera(selected)
        )
        panel.fullscreen_button.set_command(
            lambda selected=panel: self.toggle_panel_fullscreen(selected)
        )
        panel.audio_button.set_command(
            lambda selected=panel: self.toggle_audio(selected)
        )
        panel.volume_scale.configure(
            command=lambda value, selected=panel: self.change_volume(
                selected,
                int(float(value)),
            )
        )
        return panel

    def _configure_grid(self) -> None:
        """Distribui os painéis em uma grade uniforme de duas linhas."""
        for row in range(self.grid_rows):
            self.root.grid_rowconfigure(row, weight=1, uniform="row")
        for column in range(self.grid_columns):
            self.root.grid_columnconfigure(column, weight=1, uniform="column")

        for index, panel in enumerate(self.panels):
            row, column = divmod(index, self.grid_columns)
            panel.grid(
                row=row,
                column=column,
                rowspan=1,
                columnspan=1,
                sticky="nsew",
                padx=1,
                pady=1,
            )
            self._bind_panel_events(panel)

    def _bind_panel_events(self, panel: CameraPanel) -> None:
        """Permite ampliar a câmera por duplo clique no painel ou no cabeçalho."""
        for widget in (
            panel,
            panel.video_label,
            panel.title_label,
            panel.status_label,
        ):
            widget.bind(
                "<Double-Button-1>",
                lambda _event, selected=panel: self.toggle_camera(selected),
            )

    def _bind_window_events(self) -> None:
        """Registra atalhos de tela cheia e o encerramento seguro da janela."""
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Command-f>", self.toggle_fullscreen)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def refresh(self) -> None:
        """Atualiza áudio e imagens na frequência configurada da interface."""
        if self.active_audio_panel is not None and not self.audio.playing:
            self.active_audio_panel = None
            self.update_audio_icons()

        for panel in self.panels:
            panel.refresh()
        delay_ms = max(1, int(1000 / UI_FPS))
        self.root.after(delay_ms, self.refresh)

    def toggle_audio(self, panel: CameraPanel) -> None:
        """Ativa uma câmera e silencia qualquer outra que esteja tocando."""
        if self.active_audio_panel is panel and self.audio.playing:
            self.audio.stop()
            self.active_audio_panel = None
        elif self.audio.play(
            panel.worker.config,
            int(panel.volume_scale.get()),
        ):
            self.active_audio_panel = panel
        else:
            panel.status_label.config(text="ffplay não encontrado")
        self.update_audio_icons()

    def change_volume(self, panel: CameraPanel, volume: int) -> None:
        """Agenda o novo volume após o usuário parar de mover o controle."""
        if panel is not self.active_audio_panel:
            return
        if self.volume_update_id is not None:
            self.root.after_cancel(self.volume_update_id)
        self.volume_update_id = self.root.after(
            250,
            lambda selected=panel, value=volume: self.apply_volume(
                selected,
                value,
            ),
        )

    def apply_volume(self, panel: CameraPanel, volume: int) -> None:
        """Aplica o volume se a câmera ainda for a fonte de áudio ativa."""
        self.volume_update_id = None
        if panel is self.active_audio_panel and self.audio.playing:
            self.audio.set_volume(volume)

    def update_audio_icons(self) -> None:
        """Sincroniza os ícones de áudio com a câmera atualmente audível."""
        for panel in self.panels:
            icon = "audio_on" if panel is self.active_audio_panel else "audio_off"
            panel.audio_button.set_icon(icon)

    def configure_initial_geometry(self) -> None:
        """Dimensiona e centraliza a janela conforme a tela disponível."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        scale = min(max(WINDOW_SCALE, 0.5), 1.0)
        available_width = int(screen_width * scale)
        available_height = int(screen_height * scale)

        aspect_ratio = WINDOW_WIDTH / max(WINDOW_HEIGHT, 1)
        width = available_width
        height = int(width / aspect_ratio)
        if height > available_height:
            height = available_height
            width = int(height * aspect_ratio)

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def toggle_fullscreen(self, _event=None) -> None:
        """Alterna a tela cheia preservando a visualização atual."""
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
        """Guarda o layout atual e entra em tela cheia no painel indicado."""
        self.root.update_idletasks()
        self.geometry_before_fullscreen = self.root.geometry()
        self.panel_before_fullscreen = self.expanded_panel
        if panel is not None:
            self.show_camera(panel)

        self.fullscreen = True
        self.root.attributes("-fullscreen", True)
        for camera_panel in self.panels:
            camera_panel.fullscreen_button.set_icon("restore")

    def leave_fullscreen(self) -> None:
        """Sai da tela cheia e recupera geometria e layout anteriores."""
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
            panel.fullscreen_button.set_icon("fullscreen")

        if saved_geometry is not None:
            self.root.after(
                50,
                lambda geometry=saved_geometry: self.restore_geometry(geometry),
            )

    def restore_geometry(self, geometry: str) -> None:
        """Restaura a janela e força o recálculo dos painéis."""
        self.root.geometry(geometry)
        self.root.update_idletasks()
        for panel in self.panels:
            panel.video_label.update_idletasks()

    def exit_fullscreen(self, _event=None) -> None:
        """Sai da tela cheia ou retorna uma câmera ampliada ao mosaico."""
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
            rowspan=self.grid_rows,
            columnspan=self.grid_columns,
            sticky="nsew",
            padx=0,
            pady=0,
        )
        selected_panel.expand_button.set_icon("mosaic")
        self.expanded_panel = selected_panel

    def show_mosaic(self) -> None:
        """Restaura cada câmera à posição original na grade configurada."""
        for panel in self.panels:
            panel.grid_remove()

        for index, panel in enumerate(self.panels):
            row, column = divmod(index, self.grid_columns)
            panel.grid(
                row=row,
                column=column,
                rowspan=1,
                columnspan=1,
                sticky="nsew",
                padx=1,
                pady=1,
            )
            panel.expand_button.set_icon("expand")

        self.expanded_panel = None
        self.root.update_idletasks()

    def close(self) -> None:
        """Encerra áudio, leitores de vídeo e a janela principal."""
        if self.volume_update_id is not None:
            self.root.after_cancel(self.volume_update_id)
        self.audio.stop()
        for worker in self.workers:
            worker.stop()
        self.root.destroy()
