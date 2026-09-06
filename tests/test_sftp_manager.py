"""Tests unitaires pour SFTPManager."""

import stat
import unittest
from unittest.mock import MagicMock

from core.sftp_manager import SFTPManager


class TestSFTPManager(unittest.TestCase):
    """Suite de tests pour le gestionnaire SFTP."""

    def setUp(self):
        self.mock_sftp = MagicMock()
        self.sftp_manager = SFTPManager(self.mock_sftp)

    def test_list_directory_sorting(self):
        """Vérifie que les répertoires apparaissent en premier et dans l'ordre alphabétique."""
        file_attr = MagicMock()
        file_attr.filename = "zebra.txt"
        file_attr.st_mode = stat.S_IFREG | 0o644
        file_attr.st_size = 1024
        file_attr.st_mtime = 1600000000

        dir_attr = MagicMock()
        dir_attr.filename = "alpha_folder"
        dir_attr.st_mode = stat.S_IFDIR | 0o755
        dir_attr.st_size = 4096
        dir_attr.st_mtime = 1600000000

        file2_attr = MagicMock()
        file2_attr.filename = "apple.txt"
        file2_attr.st_mode = stat.S_IFREG | 0o644
        file2_attr.st_size = 512
        file2_attr.st_mtime = 1600000000

        self.mock_sftp.listdir_attr.return_value = [file_attr, dir_attr, file2_attr]

        entries = self.sftp_manager.list_directory("/home/test")

        self.assertEqual(len(entries), 3)
        self.assertTrue(entries[0].is_dir)
        self.assertEqual(entries[0].filename, "alpha_folder")

        self.assertFalse(entries[1].is_dir)
        self.assertEqual(entries[1].filename, "apple.txt")

        self.assertFalse(entries[2].is_dir)
        self.assertEqual(entries[2].filename, "zebra.txt")

    def test_change_directory(self):
        """Vérifie le changement de répertoire."""
        new_path = self.sftp_manager.change_directory("/var/www")
        self.assertEqual(new_path, "/var/www")
        self.assertEqual(self.sftp_manager.current_path, "/var/www")
        self.mock_sftp.stat.assert_called_with("/var/www")

    def test_get_file_size(self):
        """Vérifie la récupération de la taille d'un fichier."""
        mock_stat = MagicMock()
        mock_stat.st_size = 2048
        self.mock_sftp.stat.return_value = mock_stat

        size = self.sftp_manager.get_file_size("/test/file.txt")
        self.assertEqual(size, 2048)

    def test_operations(self):
        """Vérifie que les opérations de base appellent bien le client SFTP."""
        self.sftp_manager.mkdir("/new_dir")
        self.mock_sftp.mkdir.assert_called_with("/new_dir")

        self.sftp_manager.remove("/file.txt")
        self.mock_sftp.remove.assert_called_with("/file.txt")

        self.sftp_manager.rmdir("/empty_dir")
        self.mock_sftp.rmdir.assert_called_with("/empty_dir")

        self.sftp_manager.rename("/old.txt", "/new.txt")
        self.mock_sftp.rename.assert_called_with("/old.txt", "/new.txt")


if __name__ == "__main__":
    unittest.main()
