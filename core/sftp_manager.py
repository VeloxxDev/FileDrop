"""Gestionnaire des opérations SFTP (listing, upload, download, etc.).

Responsabilité : toutes les opérations fichiers sur le serveur distant.
Utilise un SFTPClient obtenu via SSHManager.
"""

import logging
import stat
from dataclasses import dataclass
from pathlib import PurePosixPath

import paramiko

from utils.formatters import format_permissions, format_timestamp

logger = logging.getLogger(__name__)


@dataclass
class RemoteFileInfo:
    """Informations sur un fichier/dossier distant."""
    filename: str
    filepath: str
    size: int
    mtime: float
    permissions: int
    is_dir: bool
    is_link: bool

    @property
    def permissions_str(self) -> str:
        return format_permissions(self.permissions)

    @property
    def mtime_str(self) -> str:
        return format_timestamp(self.mtime)


class SFTPManager:
    """Opérations SFTP sur le serveur distant."""

    def __init__(self, sftp_client: paramiko.SFTPClient):
        self._sftp = sftp_client
        self._current_path = "/"

    @property
    def current_path(self) -> str:
        return self._current_path

    def list_directory(self, path: str | None = None) -> list[RemoteFileInfo]:
        """Liste le contenu d'un répertoire distant (dossiers en tête, puis ordre alphabétique)."""
        if path is None:
            path = self._current_path

        path = str(PurePosixPath(path))
        entries = []

        for attr in self._sftp.listdir_attr(path):
            filepath = str(PurePosixPath(path) / attr.filename)
            is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
            is_link = stat.S_ISLNK(attr.st_mode) if attr.st_mode else False

            entries.append(RemoteFileInfo(
                filename=attr.filename,
                filepath=filepath,
                size=attr.st_size or 0,
                mtime=attr.st_mtime or 0,
                permissions=attr.st_mode or 0,
                is_dir=is_dir,
                is_link=is_link,
            ))

        entries.sort(key=lambda f: (not f.is_dir, f.filename.lower()))
        return entries

    def change_directory(self, path: str) -> str:
        """Valide et met à jour le répertoire distant actif."""
        new_path = str(PurePosixPath(path))
        # Valide l'existence avant d'actualiser le chemin (SFTP n'a pas de notion de dossier courant côté serveur)
        self._sftp.stat(new_path)
        self._current_path = new_path
        return self._current_path

    def get_home_directory(self) -> str:
        """Retourne le chemin absolu du dossier personnel distant normalisé."""
        return self._sftp.normalize(".")

    def upload(self, local_path: str, remote_path: str, callback=None) -> None:
        """Transfère un fichier local vers le chemin distant cible."""
        self._sftp.put(local_path, remote_path, callback=callback)
        logger.info("Upload terminé : %s → %s", local_path, remote_path)

    def download(self, remote_path: str, local_path: str, callback=None) -> None:
        """Télécharge un fichier distant vers le chemin local cible."""
        self._sftp.get(remote_path, local_path, callback=callback)
        logger.info("Download terminé : %s → %s", remote_path, local_path)

    def mkdir(self, path: str) -> None:
        """Crée un nouveau répertoire sur le serveur distant."""
        self._sftp.mkdir(path)

    def remove(self, path: str) -> None:
        """Supprime un fichier distant."""
        self._sftp.remove(path)

    def rmdir(self, path: str) -> None:
        """Supprime un répertoire distant vide."""
        self._sftp.rmdir(path)

    def rename(self, old_path: str, new_path: str) -> None:
        """Renomme ou déplace un élément distant."""
        self._sftp.rename(old_path, new_path)

    def get_file_size(self, path: str) -> int:
        """Retourne la taille d'un fichier distant en octets."""
        return self._sftp.stat(path).st_size or 0

    def close(self) -> None:
        """Ferme le canal SFTP associé."""
        if self._sftp:
            self._sftp.close()
