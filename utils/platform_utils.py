"""Utilitaires cross-platform (détection OS, chemins par défaut)."""

import os
import platform
from pathlib import Path, PurePosixPath


def get_os_name() -> str:
    """Identifie le système d'exploitation ('windows', 'linux', 'macos')."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system


def get_home_directory() -> Path:
    """Retourne le répertoire personnel de l'utilisateur."""
    return Path.home()


def get_default_ssh_key_paths() -> list[Path]:
    """Détecte les fichiers de clés SSH privées usuels présents dans ~/.ssh."""
    ssh_dir = Path.home() / ".ssh"
    key_names = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]
    return [ssh_dir / name for name in key_names if (ssh_dir / name).exists()]


def get_known_hosts_path() -> Path:
    """Localise le fichier standard known_hosts de l'utilisateur."""
    return Path.home() / ".ssh" / "known_hosts"


def get_config_directory() -> Path:
    """Garantit et retourne le dossier de configuration selon le standard de l'OS."""
    if get_os_name() == "windows":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    elif get_os_name() == "macos":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))

    config_dir = base / "FileDrop"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def normalize_remote_path(path: str) -> str:
    """Convertit un chemin distant en notation POSIX standard."""
    return str(PurePosixPath(path))


def set_window_dark_mode(hwnd: int, dark: bool = True) -> bool:
    """Active ou désactive la bordure de fenêtre sombre native via l'API DWM de Windows."""
    if get_os_name() != "windows":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        # DWMWA_USE_IMMERSIVE_DARK_MODE : 20 sur Windows 11 / Windows 10 20H1+
        # DWMWA_USE_IMMERSIVE_DARK_MODE_OLD : 19 sur Windows 10 1809 - 1909
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19

        value = ctypes.c_int(1 if dark else 0)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        if res != 0:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_OLD,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            
        # Rafraîchir la fenêtre pour appliquer la bordure immédiatement
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)

        return True
    except Exception:
        return False
