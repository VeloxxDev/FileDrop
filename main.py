"""
FileDrop — Client SFTP graphique cross-platform.

Point d'entrée de l'application.
"""

import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    import ctypes
    from PyQt6.QtGui import QIcon
    import os

    app = QApplication(sys.argv)
    app.setApplicationName("FileDrop")
    app.setApplicationVersion("0.1.0")
    
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    # Pour que l'icône s'affiche bien dans la barre des tâches Windows
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("filedrop.app.1.0")
        except Exception:
            pass

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
