"""Paramètres de l'application FileDrop."""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

from utils.platform_utils import get_config_directory

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    """Paramètres persistants de l'application."""

    theme: str = "dark"
    font_size: int = 10
    max_concurrent_transfers: int = 3
    show_hidden_files: bool = False
    default_port: int = 22
    keepalive_interval: int = 30
    connection_timeout: int = 10
    default_local_directory: str = ""

    @classmethod
    def load(cls) -> "AppSettings":
        """Charge la configuration persistée ou initialise les options par défaut."""
        config_file = get_config_directory() / "settings.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**{
                    k: v for k, v in data.items()
                    if k in cls.__dataclass_fields__
                })
            except Exception as e:
                logger.warning("Erreur chargement settings : %s", e)
        return cls()

    def save(self) -> None:
        """Enregistre la configuration actuelle dans le fichier settings.json."""
        config_file = get_config_directory() / "settings.json"
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Erreur sauvegarde settings : %s", e)
