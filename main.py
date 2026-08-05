#!/usr/bin/env python3
"""Ponto de entrada do reprodutor de câmeras RTSP VisionHub."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageTk


SPLASH_DURATION_MS = 5_000


def resource_path(relative_path: str) -> Path:
    """Localiza recursos tanto no código-fonte quanto no pacote PyInstaller."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def show_splash(root: tk.Tk) -> None:
    """Exibe a apresentação dentro da janela principal durante o carregamento."""
    image = Image.open(resource_path("assets/VisuonHub.png"))
    max_size = min(
        720,
        int(root.winfo_screenwidth() * 0.7),
        int(root.winfo_screenheight() * 0.7),
    )
    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(image)

    root.title("VisionHub — Carregando")
    root.configure(bg="black")
    width, height = image.size
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    splash = tk.Label(root, image=photo, bg="black", borderwidth=0)
    splash.image = photo
    splash.pack(fill="both", expand=True)
    root.update_idletasks()


def main() -> None:
    """Cria a janela principal e inicia o loop da interface gráfica."""
    root = tk.Tk()

    from visionhub.instance import acquire_instance_lock

    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        messagebox.showinfo(
            "VisionHub já está aberto",
            "Já existe uma instância do VisionHub em execução.",
            parent=root,
        )
        root.destroy()
        return

    show_splash(root)

    def start_application() -> None:
        """Fecha a apresentação e inicia a configuração e a aplicação."""
        for widget in root.winfo_children():
            widget.destroy()

        from visionhub.setup import ensure_initial_config

        if not ensure_initial_config(root):
            root.destroy()
            return

        from visionhub import VisionHubApp

        VisionHubApp(root)

    root.after(SPLASH_DURATION_MS, start_application)
    try:
        root.mainloop()
    finally:
        instance_lock.release()


if __name__ == "__main__":
    main()
