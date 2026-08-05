#!/usr/bin/env python3
"""Ponto de entrada do reprodutor de câmeras RTSP VisionHub."""

import tkinter as tk


def main() -> None:
    """Cria a janela principal e inicia o loop da interface gráfica."""
    root = tk.Tk()
    root.withdraw()

    from visionhub.setup import ensure_initial_config

    if not ensure_initial_config(root):
        root.destroy()
        return

    from visionhub import VisionHubApp

    root.deiconify()
    VisionHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
