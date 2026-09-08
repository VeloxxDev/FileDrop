"""Tests unitaires pour le gestionnaire de file d'attente de transferts."""

import os
import unittest
from unittest.mock import MagicMock, patch

from models.transfer_task import TransferTask, TransferDirection, TransferStatus
from core.transfer_manager import TransferManager


class TestTransferManager(unittest.TestCase):
    """Teste la logique de file d'attente, de concurrence et d'annulation."""

    def _create_manager(self):
        """Cree un TransferManager sans QApplication en mockant les signaux Qt."""
        manager = TransferManager.__new__(TransferManager)
        manager._max_concurrent = 3
        manager._pending_tasks = []
        manager._active_workers = []
        manager._transport = MagicMock()

        manager.task_added = MagicMock()
        manager.task_updated = MagicMock()
        manager.task_finished = MagicMock()
        manager.queue_changed = MagicMock()

        return manager

    def setUp(self):
        self.manager = self._create_manager()

    def test_start_transfer_creates_task(self):
        """Verifie qu'un appel a start_transfer cree une tache en attente."""
        with patch.object(self.manager, '_process_queue'):
            task = self.manager.start_transfer(
                "/local/file.txt", "/remote/file.txt", TransferDirection.UPLOAD
            )

        self.assertIsInstance(task, TransferTask)
        self.assertEqual(task.local_path, "/local/file.txt")
        self.assertEqual(task.remote_path, "/remote/file.txt")
        self.assertEqual(task.direction, TransferDirection.UPLOAD)
        self.manager.task_added.emit.assert_called_once_with(task)

    def test_cancel_pending_task(self):
        """Verifie l'annulation d'une tache en attente."""
        task = TransferTask(
            local_path="/local/test.txt",
            remote_path="/remote/test.txt",
            direction=TransferDirection.UPLOAD,
        )
        self.manager._pending_tasks.append(task)

        self.manager.cancel_transfer(task)

        self.assertEqual(task.status, TransferStatus.CANCELLED)
        self.assertNotIn(task, self.manager._pending_tasks)
        self.manager.task_updated.emit.assert_called_once_with(task)

    def test_cancel_active_task(self):
        """Verifie l'annulation d'une tache active via le worker."""
        task = TransferTask(
            local_path="/local/test.txt",
            remote_path="/remote/test.txt",
            direction=TransferDirection.UPLOAD,
        )
        mock_worker = MagicMock()
        mock_worker.task = task
        self.manager._active_workers.append(mock_worker)

        self.manager.cancel_transfer(task)

        mock_worker.cancel.assert_called_once()

    def test_cancel_all(self):
        """Verifie que cancel_all annule les workers actifs et vide la queue."""
        pending_task = TransferTask(
            local_path="/local/p.txt",
            remote_path="/remote/p.txt",
            direction=TransferDirection.UPLOAD,
        )
        self.manager._pending_tasks.append(pending_task)

        mock_worker = MagicMock()
        self.manager._active_workers.append(mock_worker)

        self.manager.cancel_all()

        mock_worker.cancel.assert_called_once()
        self.assertEqual(pending_task.status, TransferStatus.CANCELLED)
        self.assertEqual(len(self.manager._pending_tasks), 0)
        self.manager.task_updated.emit.assert_called_once_with(pending_task)

    def test_properties(self):
        """Verifie les proprietes active_count et pending_count."""
        self.assertEqual(self.manager.active_count, 0)
        self.assertEqual(self.manager.pending_count, 0)

        task = TransferTask(
            local_path="/local/t.txt",
            remote_path="/remote/t.txt",
            direction=TransferDirection.DOWNLOAD,
        )
        self.manager._pending_tasks.append(task)
        self.assertEqual(self.manager.pending_count, 1)

        mock_worker = MagicMock()
        self.manager._active_workers.append(mock_worker)
        self.assertEqual(self.manager.active_count, 1)

    def test_set_max_concurrent(self):
        """Verifie la modification de la limite de concurrence."""
        with patch.object(self.manager, '_process_queue'):
            self.manager.set_max_concurrent(5)
            self.assertEqual(self.manager._max_concurrent, 5)

            self.manager.set_max_concurrent(0)
            self.assertEqual(self.manager._max_concurrent, 1)

    def test_set_transport(self):
        """Verifie l'affectation du transport SSH."""
        mock_transport = MagicMock()
        self.manager.set_transport(mock_transport)
        self.assertEqual(self.manager._transport, mock_transport)

        self.manager.set_transport(None)
        self.assertIsNone(self.manager._transport)

    def test_process_queue_respects_concurrency(self):
        """Verifie que _process_queue ne depasse pas la limite de concurrence."""
        self.manager._max_concurrent = 2
        self.manager._active_workers = [MagicMock(), MagicMock()]

        task = TransferTask(
            local_path="/local/x.txt",
            remote_path="/remote/x.txt",
            direction=TransferDirection.UPLOAD,
        )
        self.manager._pending_tasks.append(task)

        self.manager._process_queue()

        self.assertEqual(len(self.manager._pending_tasks), 1)

    def test_process_queue_without_transport(self):
        """Verifie que _process_queue ne fait rien sans transport."""
        self.manager._transport = None

        task = TransferTask(
            local_path="/local/x.txt",
            remote_path="/remote/x.txt",
            direction=TransferDirection.UPLOAD,
        )
        self.manager._pending_tasks.append(task)
        self.manager._process_queue()

        self.assertEqual(len(self.manager._pending_tasks), 1)

    def test_on_worker_finished_removes_worker(self):
        """Verifie que la fin d'un worker le retire de la liste active."""
        task = TransferTask(
            local_path="/local/done.txt",
            remote_path="/remote/done.txt",
            direction=TransferDirection.UPLOAD,
        )
        task.status = TransferStatus.COMPLETED

        mock_worker = MagicMock()
        mock_worker.task = task
        self.manager._active_workers.append(mock_worker)

        with patch.object(self.manager, '_process_queue'):
            self.manager._on_worker_finished(task)

        self.assertEqual(len(self.manager._active_workers), 0)
        self.manager.task_finished.emit.assert_called_once_with(task)

    def test_upload_paths_with_files(self):
        """Verifie que upload_paths cree des taches pour les fichiers."""
        with patch.object(self.manager, 'start_transfer') as mock_start, \
             patch('os.path.isdir', return_value=False):
            self.manager.upload_paths(
                ["/local/a.txt", "/local/b.txt"],
                "/remote/dir",
                MagicMock(),
            )

            self.assertEqual(mock_start.call_count, 2)

    def test_download_entries_with_files(self):
        """Verifie que download_entries cree des taches pour les fichiers."""
        entry = MagicMock()
        entry.is_dir = False
        entry.filepath = "/remote/file.txt"
        entry.filename = "file.txt"

        with patch.object(self.manager, 'start_transfer') as mock_start:
            self.manager.download_entries([entry], "/local/dir", MagicMock())

            mock_start.assert_called_once_with(
                os.path.join("/local/dir", "file.txt"),
                "/remote/file.txt",
                TransferDirection.DOWNLOAD,
            )

    def test_download_directory_delegates(self):
        """Verifie que download_directory appelle _download_directory."""
        with patch.object(self.manager, '_download_directory') as mock_dl:
            self.manager.download_directory("/remote/dir", "/local/parent", MagicMock())
            mock_dl.assert_called_once()


if __name__ == "__main__":
    unittest.main()
