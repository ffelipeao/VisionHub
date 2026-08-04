#!/usr/bin/env python3
"""Ponto de entrada do reprodutor de câmeras RTSP VisionHub."""

import tkinter as tk

from visionhub import VisionHubApp


def main() -> None:
    """Cria a janela principal e inicia o loop da interface gráfica."""
    root = tk.Tk()
    VisionHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
