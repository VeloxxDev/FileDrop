"""Gestionnaire de thèmes visuels (QSS) pour FileDrop."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


from PyQt6.QtCore import QObject, QEvent
from utils.platform_utils import set_window_dark_mode

class WindowThemeFilter(QObject):
    """Filtre d'événements pour appliquer le thème sombre aux barres de titre de toutes les fenêtres (y compris QMessageBox)."""
    def __init__(self, theme_name: str, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show:
            if hasattr(obj, "isWindow") and obj.isWindow():
                try:
                    set_window_dark_mode(int(obj.winId()), dark=(self.theme_name == "dark"))
                except Exception:
                    pass
        return super().eventFilter(obj, event)


class ThemeManager:
    """Charge et applique dynamiquement les thèmes QSS (sombre / clair)."""

    STYLES_DIR = Path(__file__).resolve().parent.parent / "resources" / "styles"
    _theme_filter = None

    @classmethod
    def apply_theme(cls, theme_name: str = "dark") -> bool:
        """Applique la feuille de style QSS globale et synchronise le mode sombre natif."""
        app = QApplication.instance()
        if not app:
            logger.warning("Aucune instance QApplication trouvée.")
            return False

        qss_path = cls.STYLES_DIR / f"{theme_name.lower()}.qss"
        if not qss_path.exists():
            logger.warning("Fichier de style introuvable : %s", qss_path)
            return False

        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()
            app.setStyleSheet(stylesheet)
            
            if cls._theme_filter:
                app.removeEventFilter(cls._theme_filter)
            cls._theme_filter = WindowThemeFilter(theme_name, app)
            app.installEventFilter(cls._theme_filter)
            
            for window in app.topLevelWidgets():
                try:
                    set_window_dark_mode(int(window.winId()), dark=(theme_name == "dark"))
                except Exception:
                    pass

            logger.info("Thème appliqué : %s", theme_name)
            return True
        except Exception as e:
            logger.error("Erreur lors de l'application du thème %s : %s", theme_name, e)
            return False
