"""Boîte de dialogue des paramètres de l'application FileDrop."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QDialogButtonBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from config.settings import AppSettings
from ui.theme_manager import ThemeManager


class SettingsDialog(QDialog):
    """Dialogue de configuration des préférences de FileDrop."""

    settings_applied = pyqtSignal()

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Préférences — FileDrop")
        self.setFixedWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("🌙 Sombre", "dark")
        self._theme_combo.addItem("☀️ Clair", "light")
        current_theme_idx = 0 if self._settings.theme == "dark" else 1
        self._theme_combo.setCurrentIndex(current_theme_idx)
        form.addRow("Thème d'affichage :", self._theme_combo)

        self._concurrent_spin = QSpinBox()
        self._concurrent_spin.setRange(1, 10)
        self._concurrent_spin.setValue(self._settings.max_concurrent_transfers)
        self._concurrent_spin.setToolTip("Nombre maximal de fichiers transférés en parallèle")
        form.addRow("Transferts simultanés max :", self._concurrent_spin)

        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(self._settings.default_port)
        form.addRow("Port SSH par défaut :", self._port_spin)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(3, 120)
        self._timeout_spin.setValue(self._settings.connection_timeout)
        self._timeout_spin.setSuffix(" s")
        form.addRow("Délai de connexion (Timeout) :", self._timeout_spin)

        self._keepalive_spin = QSpinBox()
        self._keepalive_spin.setRange(5, 300)
        self._keepalive_spin.setValue(self._settings.keepalive_interval)
        self._keepalive_spin.setSuffix(" s")
        form.addRow("Intervalle Keepalive :", self._keepalive_spin)

        layout.addLayout(form)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _save_settings(self):
        """Persiste les préférences modifiées et notifie l'application."""
        old_theme = self._settings.theme
        new_theme = self._theme_combo.currentData()

        self._settings.theme = new_theme
        self._settings.max_concurrent_transfers = self._concurrent_spin.value()
        self._settings.default_port = self._port_spin.value()
        self._settings.connection_timeout = self._timeout_spin.value()
        self._settings.keepalive_interval = self._keepalive_spin.value()

        self._settings.save()

        if old_theme != new_theme:
            ThemeManager.apply_theme(new_theme)

        self.settings_applied.emit()
        self.accept()
