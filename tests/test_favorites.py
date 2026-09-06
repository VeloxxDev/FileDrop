"""Tests unitaires pour FavoritesManager et ConnectionInfo."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.favorites import FavoritesManager
from models.connection_info import ConnectionInfo, AuthMethod


class TestFavorites(unittest.TestCase):
    """Tests du système de favoris et sérialisation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.fake_config_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_connection_info_serialization(self):
        """Vérifie la sérialisation / désérialisation de ConnectionInfo."""
        conn = ConnectionInfo(
            host="ssh.example.com",
            username="testuser",
            port=2222,
            auth_method=AuthMethod.KEY_FILE,
            key_path="~/.ssh/id_ed25519",
            password="dummy_password_not_saved",
            label="Serveur Test",
        )

        data = conn.to_dict()
        self.assertNotIn("password", data)
        self.assertEqual(data["host"], "ssh.example.com")
        self.assertEqual(data["auth_method"], "KEY_FILE")

        restored = ConnectionInfo.from_dict(data)
        self.assertEqual(restored.host, conn.host)
        self.assertEqual(restored.username, conn.username)
        self.assertEqual(restored.port, conn.port)
        self.assertEqual(restored.auth_method, AuthMethod.KEY_FILE)
        self.assertEqual(restored.key_path, conn.key_path)
        self.assertIsNone(restored.password)

    def test_favorites_add_and_deduplicate(self):
        """Vérifie l'ajout et l'évitement des doublons dans FavoritesManager."""
        with patch("config.favorites.get_config_directory", return_value=self.fake_config_path):
            manager = FavoritesManager()
            self.assertEqual(len(manager.favorites), 0)

            conn1 = ConnectionInfo(host="serveur1.fr", username="user1", port=22)
            conn2 = ConnectionInfo(host="serveur2.fr", username="user2", port=22)
            conn1_dup = ConnectionInfo(host="serveur1.fr", username="user1", port=22, label="Nouveau label")

            manager.add(conn1)
            manager.add(conn2)
            self.assertEqual(len(manager.favorites), 2)

            manager.add(conn1_dup)
            self.assertEqual(len(manager.favorites), 2)
            self.assertEqual(manager.favorites[0].label, "Nouveau label")

            manager.remove(0)
            self.assertEqual(len(manager.favorites), 1)
            self.assertEqual(manager.favorites[0].host, "serveur2.fr")


if __name__ == "__main__":
    unittest.main()
