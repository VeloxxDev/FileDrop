"""Modèle de données pour les informations de connexion SSH."""

from dataclasses import dataclass
from enum import Enum, auto


class AuthMethod(Enum):
    """Méthode d'authentification SSH."""
    PASSWORD = auto()
    KEY_FILE = auto()
    AGENT = auto()


@dataclass
class ConnectionInfo:
    """Informations de connexion à un serveur SSH."""
    host: str
    username: str
    port: int = 22
    auth_method: AuthMethod = AuthMethod.PASSWORD
    password: str | None = None
    key_path: str | None = None
    key_passphrase: str | None = None
    label: str = ""

    @property
    def display_name(self) -> str:
        """Libellé personnalisé ou identifiant 'utilisateur@hôte:port'."""
        if self.label:
            return self.label
        return f"{self.username}@{self.host}:{self.port}"

    def to_dict(self) -> dict:
        """Sérialise les champs persistables en dictionnaire sans le mot de passe."""
        return {
            "host": self.host,
            "username": self.username,
            "port": self.port,
            "auth_method": self.auth_method.name,
            "key_path": self.key_path,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionInfo":
        """Reconstruit une instance ConnectionInfo depuis un dictionnaire sérialisé."""
        return cls(
            host=data["host"],
            username=data["username"],
            port=data.get("port", 22),
            auth_method=AuthMethod[data.get("auth_method", "PASSWORD")],
            key_path=data.get("key_path"),
            label=data.get("label", ""),
        )
