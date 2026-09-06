"""Tests unitaires pour AppSettings."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.settings import AppSettings


class TestAppSettings(unittest.TestCase):
    """Suite de tests pour la gestion de la configuration persistante."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_values(self):
        """Vérifie l'initialisation des paramètres par défaut."""
        settings = AppSettings()
        self.assertEqual(settings.theme, "dark")
        self.assertEqual(settings.max_concurrent_transfers, 3)
        self.assertEqual(settings.default_port, 22)
        self.assertEqual(settings.connection_timeout, 10)
        self.assertEqual(settings.keepalive_interval, 30)
        self.assertFalse(settings.show_hidden_files)

    def test_save_and_load(self):
        """Vérifie la sérialisation et la désérialisation de la configuration."""
        with patch("config.settings.get_config_directory", return_value=self.config_dir):
            settings = AppSettings(
                theme="light",
                max_concurrent_transfers=5,
                connection_timeout=20,
                keepalive_interval=45,
            )
            settings.save()

            loaded = AppSettings.load()
            self.assertEqual(loaded.theme, "light")
            self.assertEqual(loaded.max_concurrent_transfers, 5)
            self.assertEqual(loaded.connection_timeout, 20)
            self.assertEqual(loaded.keepalive_interval, 45)

    def test_load_corrupted_file(self):
        """Vérifie la tolérance aux pannes en cas de fichier settings.json corrompu."""
        with patch("config.settings.get_config_directory", return_value=self.config_dir):
            settings_file = self.config_dir / "settings.json"
            settings_file.write_text("{ unformatted invalid json content", encoding="utf-8")

            loaded = AppSettings.load()
            self.assertEqual(loaded.theme, "dark")
            self.assertEqual(loaded.default_port, 22)

    def test_load_with_unknown_fields(self):
        """Vérifie que les clés inconnues ou obsolètes sont ignorées sans erreur."""
        with patch("config.settings.get_config_directory", return_value=self.config_dir):
            settings_file = self.config_dir / "settings.json"
            payload = {
                "theme": "light",
                "obsolete_key": "dummy_value",
                "future_feature_flag": True,
            }
            settings_file.write_text(json.dumps(payload), encoding="utf-8")

            loaded = AppSettings.load()
            self.assertEqual(loaded.theme, "light")
            self.assertFalse(hasattr(loaded, "obsolete_key"))


if __name__ == "__main__":
    unittest.main()
