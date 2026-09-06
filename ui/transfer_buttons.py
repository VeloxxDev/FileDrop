"""Panneau de boutons de transfert entre les panneaux local et distant."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
)
from PyQt6.QtCore import pyqtSignal


class TransferButtons(QWidget):
    """Colonne de boutons entre le panneau local et distant.

    Signals:
        upload_requested(): L'utilisateur veut envoyer des fichiers (local → distant).
        download_requested(): L'utilisateur veut télécharger des fichiers (distant → local).
    """

    upload_requested = pyqtSignal()
    download_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(50)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(6)

        layout.addStretch()

        self._upload_btn = QPushButton("→")
        self._upload_btn.setToolTip("Envoyer vers le serveur (Upload)")
        self._upload_btn.setFixedSize(40, 40)
        self._upload_btn.setStyleSheet(
            "QPushButton { font-size: 18px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2980b9; color: white; }"
            "QPushButton:disabled { color: #666; }"
        )
        self._upload_btn.clicked.connect(self.upload_requested.emit)
        self._upload_btn.setEnabled(False)
        layout.addWidget(self._upload_btn)

        self._download_btn = QPushButton("←")
        self._download_btn.setToolTip("Télécharger depuis le serveur (Download)")
        self._download_btn.setFixedSize(40, 40)
        self._download_btn.setStyleSheet(
            "QPushButton { font-size: 18px; font-weight: bold; }"
            "QPushButton:hover { background-color: #27ae60; color: white; }"
            "QPushButton:disabled { color: #666; }"
        )
        self._download_btn.clicked.connect(self.download_requested.emit)
        self._download_btn.setEnabled(False)
        layout.addWidget(self._download_btn)

        layout.addStretch()

    def set_enabled(self, enabled: bool):
        """Active ou désactive les boutons selon l'état de la connexion."""
        self._upload_btn.setEnabled(enabled)
        self._download_btn.setEnabled(enabled)
