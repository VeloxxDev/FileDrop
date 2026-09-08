"""Gestionnaire de la file d'attente de transferts SFTP.

Responsabilite : creation des taches, gestion de la concurrence des workers,
parcours recursif des dossiers, annulation unitaire et globale.
Emet des signaux Qt pour notifier l'interface graphique.
"""

import logging
import os
from pathlib import PurePosixPath

from PyQt6.QtCore import QObject, pyqtSignal

from core.transfer_worker import TransferWorker
from models.transfer_task import TransferTask, TransferDirection, TransferStatus

logger = logging.getLogger(__name__)


class TransferManager(QObject):
    """Orchestre les transferts SFTP avec file d'attente et concurrence limitee.

    Signals:
        task_added(task): Une nouvelle tache a ete creee et ajoutee a la queue.
        task_updated(task): Progression ou changement de statut d'une tache.
        task_finished(task): Un transfert est termine (succes, echec ou annule).
        queue_changed(active_count, pending_count): Les compteurs ont change.
    """

    task_added = pyqtSignal(TransferTask)
    task_updated = pyqtSignal(TransferTask)
    task_finished = pyqtSignal(TransferTask)
    queue_changed = pyqtSignal(int, int)

    def __init__(self, max_concurrent: int = 3, parent=None):
        super().__init__(parent)
        self._max_concurrent = max_concurrent
        self._pending_tasks: list[TransferTask] = []
        self._active_workers: list[TransferWorker] = []
        self._transport = None

    @property
    def active_count(self) -> int:
        """Nombre de transferts actifs."""
        return len(self._active_workers)

    @property
    def pending_count(self) -> int:
        """Nombre de transferts en attente."""
        return len(self._pending_tasks)

    def set_transport(self, transport) -> None:
        """Definit le transport SSH utilise pour creer les canaux SFTP des workers."""
        self._transport = transport

    def set_max_concurrent(self, value: int) -> None:
        """Met a jour la limite de concurrence et traite la queue si possible."""
        self._max_concurrent = max(1, value)
        self._process_queue()

    def start_transfer(
        self,
        local_path: str,
        remote_path: str,
        direction: TransferDirection,
    ) -> TransferTask:
        """Cree une tache de transfert, l'ajoute a la queue et lance le traitement."""
        task = TransferTask(
            local_path=local_path,
            remote_path=remote_path,
            direction=direction,
        )

        self._pending_tasks.append(task)
        self.task_added.emit(task)
        self._process_queue()

        return task

    def upload_paths(self, paths: list[str], remote_dir: str, sftp_manager) -> None:
        """Met en file d'attente l'upload d'une liste de chemins locaux (fichiers et dossiers)."""
        for local_path in paths:
            if os.path.isdir(local_path):
                self._upload_directory(local_path, remote_dir, sftp_manager)
            else:
                filename = os.path.basename(local_path)
                remote_path = str(PurePosixPath(remote_dir) / filename)
                self.start_transfer(local_path, remote_path, TransferDirection.UPLOAD)

    def download_entries(self, entries: list, local_dir: str, sftp_manager) -> None:
        """Met en file d'attente le download d'une liste d'entrees distantes (fichiers et dossiers)."""
        for entry in entries:
            if entry.is_dir:
                self._download_directory(entry.filepath, local_dir, sftp_manager)
            else:
                local_path = os.path.join(local_dir, entry.filename)
                self.start_transfer(local_path, entry.filepath, TransferDirection.DOWNLOAD)

    def download_directory(self, remote_dir_path: str, local_parent: str, sftp_manager) -> None:
        """Telecharge recursivement un dossier distant (point d'entree public)."""
        self._download_directory(remote_dir_path, local_parent, sftp_manager)

    def cancel_transfer(self, task: TransferTask) -> None:
        """Annule un transfert en attente ou actif."""
        if task in self._pending_tasks:
            self._pending_tasks.remove(task)
            task.status = TransferStatus.CANCELLED
            self.task_updated.emit(task)
            logger.info("Tache en attente annulee : %s", task.filename)
            self._emit_queue_changed()
            return

        for worker in self._active_workers:
            if worker.task is task:
                worker.cancel()
                logger.info("Annulation demandee : %s", task.filename)
                break

    def cancel_all(self) -> None:
        """Annule tous les transferts actifs et vide la queue."""
        for worker in self._active_workers:
            worker.cancel()

        for task in self._pending_tasks:
            task.status = TransferStatus.CANCELLED
            self.task_updated.emit(task)

        self._pending_tasks.clear()
        self._emit_queue_changed()

    def wait_for_workers(self, timeout_ms: int = 1000) -> None:
        """Attend la fin des workers actifs avec un timeout par worker."""
        for worker in self._active_workers:
            worker.wait(timeout_ms)

    def _process_queue(self) -> None:
        """Demarre les transferts en attente jusqu'a concurrence maximale."""
        if not self._transport:
            return

        while self._pending_tasks and len(self._active_workers) < self._max_concurrent:
            task = self._pending_tasks.pop(0)

            worker = TransferWorker(self._transport, task, parent=self)
            worker.progress_updated.connect(self._on_worker_progress)
            worker.transfer_finished.connect(self._on_worker_finished)

            self._active_workers.append(worker)
            worker.start()

            direction_label = "Upload" if task.direction == TransferDirection.UPLOAD else "Download"
            logger.info("%s demarre : %s", direction_label, task.filename)

        self._emit_queue_changed()

    def _on_worker_progress(self, task: TransferTask, bytes_done: int, total: int) -> None:
        """Relaye la progression d'un worker vers l'interface graphique."""
        self.task_updated.emit(task)

    def _on_worker_finished(self, task: TransferTask) -> None:
        """Traite la fin d'un worker et lance le transfert suivant."""
        self._active_workers = [w for w in self._active_workers if w.task is not task]

        if task.status == TransferStatus.COMPLETED:
            logger.info("Termine : %s", task.filename)
        elif task.status == TransferStatus.FAILED:
            logger.error("Echec : %s -- %s", task.filename, task.error_message)
        elif task.status == TransferStatus.CANCELLED:
            logger.info("Annule : %s", task.filename)

        self.task_finished.emit(task)
        self._process_queue()

    def _upload_directory(self, local_dir_path: str, remote_parent: str, sftp_manager) -> None:
        """Televerse recursivement un dossier local vers le serveur distant."""
        dir_name = os.path.basename(local_dir_path)
        remote_dir = str(PurePosixPath(remote_parent) / dir_name)

        try:
            sftp_manager.mkdir(remote_dir)
            logger.info("Dossier cree : %s", remote_dir)
        except IOError:
            pass

        try:
            for item in os.listdir(local_dir_path):
                item_path = os.path.join(local_dir_path, item)
                if os.path.isdir(item_path):
                    self._upload_directory(item_path, remote_dir, sftp_manager)
                else:
                    remote_path = str(PurePosixPath(remote_dir) / item)
                    self.start_transfer(item_path, remote_path, TransferDirection.UPLOAD)
        except Exception as e:
            logger.error("Erreur parcours upload %s : %s", local_dir_path, e)

    def _download_directory(self, remote_dir_path: str, local_parent: str, sftp_manager) -> None:
        """Telecharge recursivement un dossier distant vers le systeme local."""
        dir_name = PurePosixPath(remote_dir_path).name
        local_dir = os.path.join(local_parent, dir_name)

        os.makedirs(local_dir, exist_ok=True)
        logger.info("Dossier cree localement : %s", local_dir)

        try:
            entries = sftp_manager.list_directory(remote_dir_path)
            for entry in entries:
                if entry.is_dir:
                    self._download_directory(entry.filepath, local_dir, sftp_manager)
                else:
                    local_path = os.path.join(local_dir, entry.filename)
                    self.start_transfer(local_path, entry.filepath, TransferDirection.DOWNLOAD)
        except Exception as e:
            logger.error("Erreur parcours download %s : %s", remote_dir_path, e)

    def _emit_queue_changed(self) -> None:
        """Emet le signal de changement de compteurs."""
        self.queue_changed.emit(self.active_count, self.pending_count)
