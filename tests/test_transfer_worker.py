"""Tests unitaires pour TransferWorker."""

import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QCoreApplication

from core.transfer_worker import TransferWorker
from models.transfer_task import TransferTask, TransferDirection, TransferStatus


class TestTransferWorker(unittest.TestCase):
    """Suite de tests pour le worker de transfert."""

    @classmethod
    def setUpClass(cls):
        # Initialise QApplication si besoin pour les signaux Qt
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_upload_flow(self):
        """Vérifie le flux complet d'un upload réussi."""
        mock_transport = MagicMock()
        mock_sftp = MagicMock()

        task = TransferTask(
            local_path="C:/dummy/local.txt",
            remote_path="/remote/path/remote.txt",
            direction=TransferDirection.UPLOAD,
        )

        with patch("paramiko.SFTPClient.from_transport", return_value=mock_sftp):
            with patch("os.path.getsize", return_value=5000):
                worker = TransferWorker(mock_transport, task)

                finished_tasks = []
                worker.transfer_finished.connect(finished_tasks.append)

                worker.run()

                self.assertEqual(task.status, TransferStatus.COMPLETED)
                self.assertEqual(task.progress, 1.0)
                mock_sftp.put.assert_called_once()
                self.assertEqual(len(finished_tasks), 1)

    def test_download_flow(self):
        """Vérifie le flux complet d'un download réussi."""
        mock_transport = MagicMock()
        mock_sftp = MagicMock()
        mock_stat = MagicMock()
        mock_stat.st_size = 8000
        mock_sftp.stat.return_value = mock_stat

        task = TransferTask(
            local_path="C:/dummy/download.txt",
            remote_path="/remote/download.txt",
            direction=TransferDirection.DOWNLOAD,
        )

        with patch("paramiko.SFTPClient.from_transport", return_value=mock_sftp):
            worker = TransferWorker(mock_transport, task)
            worker.run()

            self.assertEqual(task.status, TransferStatus.COMPLETED)
            mock_sftp.get.assert_called_once()

    def test_cancellation(self):
        """Vérifie la bonne gestion de l'annulation d'un transfert."""
        mock_transport = MagicMock()
        mock_sftp = MagicMock()

        task = TransferTask(
            local_path="C:/dummy/cancel.txt",
            remote_path="/remote/cancel.txt",
            direction=TransferDirection.UPLOAD,
        )

        def mock_put(local, remote, callback=None):
            if callback:
                callback(100, 1000)

        mock_sftp.put.side_effect = mock_put

        with patch("paramiko.SFTPClient.from_transport", return_value=mock_sftp):
            with patch("os.path.getsize", return_value=1000):
                worker = TransferWorker(mock_transport, task)
                worker.cancel()
                worker.run()

                self.assertEqual(task.status, TransferStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
