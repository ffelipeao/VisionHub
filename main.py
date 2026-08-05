#!/usr/bin/env python3
"""Ponto de entrada do reprodutor de câmeras RTSP VisionHub."""

import tkinter as tk
from tkinter import messagebox


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

    from visionhub.setup import ensure_initial_config

    if not ensure_initial_config(root):
        instance_lock.release()
        root.destroy()
        return

    from visionhub import VisionHubApp

    VisionHubApp(root)
    try:
        root.mainloop()
    finally:
        instance_lock.release()


if __name__ == "__main__":
    main()
