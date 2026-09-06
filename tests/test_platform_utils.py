"""Tests unitaires pour platform_utils."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.platform_utils import (
    get_os_name,
    get_home_directory,
    get_known_hosts_path,
    get_config_directory,
    normalize_remote_path,
    set_window_dark_mode,
)


class TestPlatformUtils(unittest.TestCase):
    """Suite de tests pour les fonctions d'intégration au système d'exploitation."""

    def test_get_os_name(self):
        """Vérifie la détection et la normalisation des noms d'OS."""
        with patch("platform.system", return_value="Windows"):
            self.assertEqual(get_os_name(), "windows")

        with patch("platform.system", return_value="Linux"):
            self.assertEqual(get_os_name(), "linux")

        with patch("platform.system", return_value="Darwin"):
            self.assertEqual(get_os_name(), "macos")

    def test_get_home_directory(self):
        """Vérifie la détection du répertoire personnel."""
        self.assertEqual(get_home_directory(), Path.home())

    def test_get_known_hosts_path(self):
        """Vérifie la localisation standard de known_hosts."""
        expected = Path.home() / ".ssh" / "known_hosts"
        self.assertEqual(get_known_hosts_path(), expected)

    def test_normalize_remote_path(self):
        """Vérifie la conversion en syntaxe POSIX standard."""
        self.assertEqual(normalize_remote_path("var/www/html"), "var/www/html")
        self.assertEqual(normalize_remote_path(r"home\user\documents"), "home/user/documents")

    def test_get_config_directory_windows(self):
        """Vérifie le chemin de configuration sous Windows."""
        with patch("utils.platform_utils.get_os_name", return_value="windows"), \
             patch.dict(os.environ, {"APPDATA": "C:\\AppData"}):
            with patch("pathlib.Path.mkdir"):
                config_dir = get_config_directory()
                self.assertEqual(config_dir, Path("C:\\AppData\\FileDrop"))

    def test_get_config_directory_macos(self):
        """Vérifie le chemin de configuration sous macOS."""
        with patch("utils.platform_utils.get_os_name", return_value="macos"):
            with patch("pathlib.Path.mkdir"):
                config_dir = get_config_directory()
                expected = Path.home() / "Library" / "Application Support" / "FileDrop"
                self.assertEqual(config_dir, expected)

    def test_get_config_directory_linux(self):
        """Vérifie le chemin de configuration sous Linux."""
        with patch("utils.platform_utils.get_os_name", return_value="linux"), \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"}):
            with patch("pathlib.Path.mkdir"):
                config_dir = get_config_directory()
                self.assertEqual(config_dir, Path("/custom/config/FileDrop"))

    def test_set_window_dark_mode_non_windows(self):
        """Vérifie que la fonction retourne False silencieusement sur les OS non-Windows."""
        with patch("utils.platform_utils.get_os_name", return_value="linux"):
            self.assertFalse(set_window_dark_mode(12345, dark=True))

        with patch("utils.platform_utils.get_os_name", return_value="macos"):
            self.assertFalse(set_window_dark_mode(12345, dark=True))


if __name__ == "__main__":
    unittest.main()
