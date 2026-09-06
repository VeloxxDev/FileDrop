"""Gestion des connexions favorites / historique."""

import json
import logging

from models.connection_info import ConnectionInfo
from utils.platform_utils import get_config_directory

logger = logging.getLogger(__name__)


class FavoritesManager:
    """Sauvegarde et chargement des connexions favorites."""

    def __init__(self):
        self._favorites: list[ConnectionInfo] = []
        self._file_path = get_config_directory() / "favorites.json"
        self.load()

    @property
    def favorites(self) -> list[ConnectionInfo]:
        """Copie défensive de la liste des favoris."""
        return self._favorites.copy()

    def add(self, connection: ConnectionInfo) -> None:
        """Insère ou remonte une connexion en tête des favoris sans doublon."""
        # Éviter les doublons (même host + user + port)
        self._favorites = [
            f for f in self._favorites
            if not (
                f.host == connection.host
                and f.username == connection.username
                and f.port == connection.port
            )
        ]
        self._favorites.insert(0, connection)
        self.save()

    def remove(self, index: int) -> None:
        """Supprime le favori à l'index spécifié."""
        if 0 <= index < len(self._favorites):
            self._favorites.pop(index)
            self.save()

    def load(self) -> None:
        """Charge l'historique des favoris depuis le fichier JSON."""
        if self._file_path.exists():
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._favorites = [
                    ConnectionInfo.from_dict(entry) for entry in data
                ]
                logger.info("%d favoris chargés.", len(self._favorites))
            except Exception as e:
                logger.warning("Erreur chargement favoris : %s", e)
                self._favorites = []

    def save(self) -> None:
        """Persiste les favoris actuels dans le fichier JSON."""
        try:
            data = [fav.to_dict() for fav in self._favorites]
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Erreur sauvegarde favoris : %s", e)
