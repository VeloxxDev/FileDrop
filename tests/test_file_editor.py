"""Tests unitaires pour RemoteFileEditor."""

import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QCoreApplication

from core.file_editor import RemoteFileEditor


class TestRemoteFileEditor(unittest.TestCase):
    """Suite de tests pour l'éditeur de fichiers distants."""

    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.editor = RemoteFileEditor()

    def tearDown(self):
        self.editor.cleanup()

    @patch("core.file_editor.QDesktopServices.openUrl")
    def test_open_remote_file_isolation(self, mock_open_url):
        """Vérifie que deux fichiers de même nom dans des dossiers différents ont des chemins isolés."""
        mock_sftp = MagicMock()

        path1 = self.editor.open_remote_file(mock_sftp, "/var/log/app.log")
        path2 = self.editor.open_remote_file(mock_sftp, "/etc/nginx/app.log")

        self.assertNotEqual(path1, path2)
        self.assertEqual(os.path.basename(path1), "app.log")
        self.assertEqual(os.path.basename(path2), "app.log")
        self.assertEqual(mock_sftp.download.call_count, 2)

    @patch("core.file_editor.QDesktopServices.openUrl")
    def test_open_same_remote_file_reuses_path(self, mock_open_url):
        """Vérifie que l'ouverture du même fichier distant réutilise le chemin existant."""
        mock_sftp = MagicMock()

        path1 = self.editor.open_remote_file(mock_sftp, "/home/user/document.txt")
        open(path1, "w", encoding="utf-8").close()

        path2 = self.editor.open_remote_file(mock_sftp, "/home/user/document.txt")

        self.assertEqual(path1, path2)
        self.assertEqual(mock_sftp.download.call_count, 1)

    @patch("core.file_editor.QDesktopServices.openUrl")
    def test_cleanup_and_reopen(self, mock_open_url):
        """Vérifie le nettoyage complet et la recréation du dossier temporaire après déconnexion."""
        mock_sftp = MagicMock()

        path = self.editor.open_remote_file(mock_sftp, "/tmp/test.txt")
        open(path, "w", encoding="utf-8").close()
        self.assertTrue(os.path.exists(path))

        temp_dir = self.editor._temp_dir
        self.editor.cleanup()

        self.assertFalse(os.path.exists(temp_dir))

        new_path = self.editor.open_remote_file(mock_sftp, "/tmp/new.txt")
        self.assertTrue(os.path.exists(os.path.dirname(new_path)))


if __name__ == "__main__":
    unittest.main()
