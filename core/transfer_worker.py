"""Workers de transfert SFTP dans des threads séparés.

Chaque worker ouvre son propre canal SFTP sur le transport SSH existant
pour garantir la thread safety (SFTPClient n'est PAS thread-safe).
"""

import logging
import os

import paramiko
from PyQt6.QtCore import QThread, pyqtSignal

from models.transfer_task import TransferTask, TransferDirection, TransferStatus

logger = logging.getLogger(__name__)


class TransferWorker(QThread):
    """Thread de transfert d'un fichier (upload ou download).

    Signals:
        progress_updated(task, bytes_transferred, total_bytes):
            Émis à chaque chunk transféré.
        transfer_finished(task):
            Émis quand le transfert est terminé (succès ou échec).
    """

    progress_updated = pyqtSignal(TransferTask, int, int)
    transfer_finished = pyqtSignal(TransferTask)

    def __init__(
        self,
        transport: paramiko.Transport,
        task: TransferTask,
        parent=None,
    ):
        super().__init__(parent)
        self._transport = transport
        self._task = task
        self._cancelled = False

    @property
    def task(self) -> TransferTask:
        return self._task

    def cancel(self) -> None:
        """Déclenche l'interruption du transfert en cours."""
        self._cancelled = True

    def run(self) -> None:
        """Exécute l'envoi ou le téléchargement sur un canal SFTP dédié."""
        sftp = None
        try:
            sftp = paramiko.SFTPClient.from_transport(self._transport)
            self._task.status = TransferStatus.IN_PROGRESS

            if self._task.direction == TransferDirection.UPLOAD:
                self._task.file_size = os.path.getsize(self._task.local_path)
            else:
                self._task.file_size = sftp.stat(self._task.remote_path).st_size or 0

            def on_progress(bytes_transferred: int, total_bytes: int) -> None:
                if self._cancelled:
                    raise InterruptedError("Transfert annulé")
                self._task.bytes_transferred = bytes_transferred
                self._task.progress = bytes_transferred / max(total_bytes, 1)
                self.progress_updated.emit(
                    self._task, bytes_transferred, total_bytes
                )

            if self._task.direction == TransferDirection.UPLOAD:
                sftp.put(
                    self._task.local_path,
                    self._task.remote_path,
                    callback=on_progress,
                )
            else:
                sftp.get(
                    self._task.remote_path,
                    self._task.local_path,
                    callback=on_progress,
                )

            self._task.status = TransferStatus.COMPLETED
            self._task.progress = 1.0
            logger.info("Transfert terminé : %s", self._task.filename)

        except InterruptedError:
            self._task.status = TransferStatus.CANCELLED
            logger.info("Transfert annulé : %s", self._task.filename)

        except Exception as e:
            self._task.status = TransferStatus.FAILED
            self._task.error_message = str(e)
            logger.error("Erreur de transfert : %s — %s", self._task.filename, e)

        finally:
            if sftp:
                sftp.close()
            self.transfer_finished.emit(self._task)
