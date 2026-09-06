"""Édition de fichiers distants.

Workflow : télécharger dans un dossier temporaire → ouvrir avec l'éditeur
par défaut → surveiller les modifications → re-uploader à la sauvegarde.
"""

import logging
import tempfile
import os
import shutil
from pathlib import PurePosixPath

from PyQt6.QtCore import QObject, QFileSystemWatcher, QUrl, pyqtSignal, QTimer
from PyQt6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)


class RemoteFileEditor(QObject):
    """Gère l'édition de fichiers distants.

    Signals:
        file_modified(local_path, remote_path):
            Émis quand un fichier édité a été modifié localement.
        upload_needed(local_path, remote_path):
            Émis pour demander le re-upload du fichier modifié.
    """

    file_modified = pyqtSignal(str, str)
    upload_needed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._tracked_files: dict[str, str] = {}
        self._temp_dir = tempfile.mkdtemp(prefix="filedrop_edit_")

        self._watcher.fileChanged.connect(self._on_file_changed)

    def open_remote_file(self, sftp_manager, remote_path: str) -> str:
        """Télécharge une copie temporaire du fichier distant et lance l'éditeur par défaut."""
        # Recrée le dossier temporaire si cleanup() a été appelé lors d'une déconnexion précédente
        if not os.path.exists(self._temp_dir):
            self._temp_dir = tempfile.mkdtemp(prefix="filedrop_edit_")

        # Réutilise l'instance locale si le fichier est déjà ouvert pour éviter un re-téléchargement
        for path, r_path in self._tracked_files.items():
            if r_path == remote_path and os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
                return path

        filename = PurePosixPath(remote_path).name
        # Sous-dossier isolé par fichier pour éviter les collisions de noms entre fichiers distants
        file_dir = tempfile.mkdtemp(dir=self._temp_dir)
        local_path = os.path.join(file_dir, filename)

        sftp_manager.download(remote_path, local_path)

        self._tracked_files[local_path] = remote_path
        self._watcher.addPath(local_path)

        QDesktopServices.openUrl(QUrl.fromLocalFile(local_path))

        logger.info("Édition distante : %s → %s", remote_path, local_path)
        return local_path

    def _on_file_changed(self, local_path: str) -> None:
        """Traite les événements de modification notifiés par le watcher."""
        if local_path not in self._tracked_files:
            return

        remote_path = self._tracked_files[local_path]

        # Sur Windows, certains éditeurs recréent le fichier (sauvegarde atomique)
        if not os.path.exists(local_path):
            QTimer.singleShot(200, lambda: self._re_add_and_emit(local_path, remote_path))
            return

        self._re_add_and_emit(local_path, remote_path)

    def _re_add_and_emit(self, local_path: str, remote_path: str):
        """Réenregistre le chemin auprès du watcher après écriture et signale le besoin d'envoi."""
        if os.path.exists(local_path):
            if local_path not in self._watcher.files():
                self._watcher.addPath(local_path)
            logger.info("Fichier édité modifié : %s", local_path)
            self.upload_needed.emit(local_path, remote_path)

    def stop_tracking(self, local_path: str) -> None:
        """Retire un fichier de la surveillance."""
        if local_path in self._tracked_files:
            self._watcher.removePath(local_path)
            del self._tracked_files[local_path]

    def cleanup(self) -> None:
        """Supprime le dossier temporaire et détache toutes les surveillances actives."""
        for local_path in list(self._tracked_files.keys()):
            self.stop_tracking(local_path)
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
