"""Tests unitaires pour les fonctions de formatage."""

import unittest
from utils.formatters import (
    format_size,
    format_permissions,
    format_transfer_speed,
)


class TestFormatters(unittest.TestCase):
    """Tests des fonctions utilitaires de formatage."""

    def test_format_size(self):
        """Vérifie la conversion en unités lisibles (o, Ko, Mo, Go)."""
        self.assertEqual(format_size(0), "0 o")
        self.assertEqual(format_size(500), "500 o")
        self.assertEqual(format_size(1024), "1.0 Ko")
        self.assertEqual(format_size(1024 * 1024), "1.0 Mo")
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0 Go")
        self.assertEqual(format_size(-10), "?")

    def test_format_permissions(self):
        """Vérifie le formatage des permissions octales en chaîne rwx."""
        self.assertEqual(format_permissions(0o755), "rwxr-xr-x")
        self.assertEqual(format_permissions(0o644), "rw-r--r--")
        self.assertEqual(format_permissions(0o700), "rwx------")

    def test_format_transfer_speed(self):
        """Vérifie le calcul et le formatage de la vitesse de transfert."""
        self.assertEqual(format_transfer_speed(0), "0 o/s")
        self.assertEqual(format_transfer_speed(1024), "1.0 Ko/s")
        self.assertEqual(format_transfer_speed(1024 * 1024 * 5.5), "5.5 Mo/s")


if __name__ == "__main__":
    unittest.main()
