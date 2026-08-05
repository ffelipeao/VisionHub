"""Assistente de configuração inicial e armazenamento seguro da senha."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import keyring
from dotenv import load_dotenv, set_key, unset_key


SERVICE_NAME = "VisionHub"
PASSWORD_PLACEHOLDERS = {"troque_por_sua_senha", "senha"}
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_PACKAGED = getattr(sys, "frozen", False)
CONFIG_DIR = Path.home() / ".visionhub" if IS_PACKAGED else PROJECT_ROOT
CONFIG_FILE = CONFIG_DIR / ".env"


def _credential_account(host: str, user: str) -> str:
    """Identifica uma credencial sem registrar a senha no arquivo local."""
    return f"{host}:{user}"


def _stored_password(host: str, user: str) -> str:
    """Obtém a senha do ambiente ou do cofre seguro do sistema operacional."""
    password = os.getenv("NVR_PASSWORD", "").strip()
    if password or not host or not user:
        return password
    try:
        return keyring.get_password(
            SERVICE_NAME,
            _credential_account(host, user),
        ) or ""
    except keyring.errors.KeyringError:
        return ""


class InitialSetupDialog(tk.Toplevel):
    """Solicita os dados mínimos necessários para acessar o NVR."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.result: dict[str, str] | None = None
        self.title("Configuração inicial do VisionHub")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        content = ttk.Frame(self, padding=20)
        content.grid(sticky="nsew")

        ttk.Label(
            content,
            text="Informe os dados de acesso ao NVR",
            font=("Helvetica", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        self.host = self._field(content, 1, "IP ou nome do NVR", "")
        self.port = self._field(content, 2, "Porta RTSP", "554")
        self.user = self._field(content, 3, "Usuário", "")
        self.password = self._field(content, 4, "Senha", "", show="•")

        ttk.Label(
            content,
            text="A senha será protegida pelo cofre de credenciais do sistema.",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 16))

        buttons = ttk.Frame(content)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(buttons, text="Salvar e continuar", command=self._save).pack(
            side="left"
        )

        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(master)
        self.grab_set()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.host.focus_set()

    @staticmethod
    def _field(
        parent: ttk.Frame,
        row: int,
        label: str,
        initial: str,
        show: str = "",
    ) -> ttk.Entry:
        """Adiciona um campo rotulado ao formulário."""
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5
        )
        entry = ttk.Entry(parent, width=34, show=show)
        entry.insert(0, initial)
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        return entry

    def _save(self) -> None:
        """Valida os campos e devolve os dados preenchidos."""
        host = self.host.get().strip()
        port = self.port.get().strip()
        user = self.user.get().strip()
        password = self.password.get()

        if not host or not user or not password:
            messagebox.showerror(
                "Dados incompletos",
                "Informe o endereço do NVR, o usuário e a senha.",
                parent=self,
            )
            return
        try:
            port_number = int(port)
        except ValueError:
            port_number = 0
        if not 1 <= port_number <= 65535:
            messagebox.showerror(
                "Porta inválida",
                "Informe uma porta RTSP entre 1 e 65535.",
                parent=self,
            )
            return

        self.result = {
            "NVR_IP": host,
            "NVR_RTSP_PORT": str(port_number),
            "NVR_USER": user,
            "NVR_PASSWORD": password,
        }
        self.destroy()


def ensure_initial_config(root: tk.Tk) -> bool:
    """Exibe o assistente quando faltam dados e persiste o resultado."""
    load_dotenv(CONFIG_FILE, override=True)
    host = os.getenv("NVR_IP", "").strip()
    user = os.getenv("NVR_USER", "").strip()
    plaintext_password = os.getenv("NVR_PASSWORD", "").strip()

    if (
        IS_PACKAGED
        and host
        and user
        and plaintext_password
        and plaintext_password not in PASSWORD_PLACEHOLDERS
    ):
        root.title("VisionHub — Protegendo credenciais")
        root.geometry("460x120")
        migration_status = ttk.Label(
            root,
            text="Protegendo a senha no cofre de credenciais do sistema…",
            padding=24,
        )
        migration_status.pack(fill="both", expand=True)
        root.update_idletasks()
        root.lift()
        try:
            keyring.set_password(
                SERVICE_NAME,
                _credential_account(host, user),
                plaintext_password,
            )
            unset_key(CONFIG_FILE, "NVR_PASSWORD")
            CONFIG_FILE.chmod(0o600)
            os.environ["NVR_PASSWORD"] = plaintext_password
        except (OSError, keyring.errors.KeyringError) as error:
            messagebox.showerror(
                "Não foi possível proteger a senha",
                "A senha existente não foi migrada para o cofre seguro. "
                f"Detalhes: {error}",
                parent=root,
            )
            return False
        finally:
            migration_status.destroy()
        return True

    stored_password = _stored_password(host, user)
    if (
        host
        and user
        and plaintext_password not in PASSWORD_PLACEHOLDERS
        and stored_password
    ):
        os.environ["NVR_PASSWORD"] = stored_password
        return True

    dialog = InitialSetupDialog(root)
    root.wait_window(dialog)
    if dialog.result is None:
        return False

    values = dialog.result
    try:
        keyring.set_password(
            SERVICE_NAME,
            _credential_account(values["NVR_IP"], values["NVR_USER"]),
            values["NVR_PASSWORD"],
        )
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.touch(exist_ok=True)
        for name in ("NVR_IP", "NVR_RTSP_PORT", "NVR_USER"):
            set_key(CONFIG_FILE, name, values[name], quote_mode="auto")
        unset_key(CONFIG_FILE, "NVR_PASSWORD")
        CONFIG_FILE.chmod(0o600)
    except (OSError, keyring.errors.KeyringError) as error:
        messagebox.showerror(
            "Não foi possível salvar",
            "Os dados não foram armazenados. Verifique o cofre de credenciais "
            f"do sistema e tente novamente.\n\nDetalhes: {error}",
            parent=root,
        )
        return False

    for name, value in values.items():
        os.environ[name] = value
    return True
