"""Modèle de données pour les tâches de transfert."""

from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class TransferDirection(Enum):
    """Direction du transfert."""
    UPLOAD = auto()
    DOWNLOAD = auto()


class TransferStatus(Enum):
    """État d'une tâche de transfert."""
    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class TransferTask:
    """Représente une tâche de transfert de fichier."""
    local_path: str
    remote_path: str
    direction: TransferDirection
    file_size: int = 0
    status: TransferStatus = TransferStatus.QUEUED
    progress: float = 0.0
    bytes_transferred: int = 0
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    is_directory: bool = False

    @property
    def progress_percent(self) -> int:
        """Progression normalisée de 0 à 100 pour les composants d'interface."""
        return int(self.progress * 100)

    @property
    def filename(self) -> str:
        """Nom du fichier déduit du chemin selon le sens du transfert."""
        import os
        if self.direction == TransferDirection.UPLOAD:
            return os.path.basename(self.local_path)
        else:
            return self.remote_path.rsplit("/", 1)[-1]
