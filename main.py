#!/usr/bin/env python3
"""Ponto de entrada do reprodutor de câmeras RTSP VigiaGrid."""

import tkinter as tk

from vigiagrid import VigiaGridApp


def main() -> None:
    """Cria a janela principal e inicia o loop da interface gráfica."""
    root = tk.Tk()
    VigiaGridApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
