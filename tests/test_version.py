"""Tests pour la version de l'application."""

import unittest
import re
from __version__ import __version__


class TestVersion(unittest.TestCase):
    """Vérifie la cohérence du numéro de version."""

    def test_version_format(self):
        self.assertIsInstance(__version__, str)
        pattern = r"^\d+\.\d+\.\d+$"
        self.assertTrue(re.match(pattern, __version__), f"Format de version invalide: {__version__}")


if __name__ == "__main__":
    unittest.main()
