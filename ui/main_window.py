"""Fenêtre principale de FileDrop.

Orchestre la barre de connexion, l'explorateur double panneau (local et distant),
le gestionnaire de transferts, le terminal interactif et les logs.
"""

import logging
import os

from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTextEdit,
    QTabWidget,
    QStatusBar,
    QMessageBox,
)
from PyQt6.QtCore import QTimer

from ui.connection_bar import ConnectionBar
from ui.local_panel import LocalPanel
from ui.remote_panel import RemotePanel
from ui.transfer_buttons import TransferButtons
from ui.transfer_queue import TransferQueueWidget
from ui.terminal_widget import TerminalWidget
from core.ssh_manager import SSHManager
from core.sftp_manager import SFTPManager
from core.transfer_manager import TransferManager
from core.file_editor import RemoteFileEditor
from config.settings import AppSettings
from models.transfer_task import TransferTask, TransferDirection, TransferStatus
from models.connection_info import ConnectionInfo
from ui.theme_manager import ThemeManager
from ui.settings_dialog import SettingsDialog
from utils.platform_utils import set_window_dark_mode
from PyQt6.QtGui import QAction
from __version__ import __version__

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """Handler de logging qui redirige vers un QTextEdit."""

    def __init__(self, text_widget: QTextEdit):
        super().__init__()
        self._text_widget = text_widget

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        color_map = {
            logging.DEBUG: "#888888",
            logging.INFO: "#ffffff",
            logging.WARNING: "#f39c12",
            logging.ERROR: "#e74c3c",
            logging.CRITICAL: "#ff0000",
        }
        color = color_map.get(record.levelno, "#ffffff")
        self._text_widget.append(f'<span style="color:{color}">{msg}</span>')


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application FileDrop."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileDrop")
        self.setMinimumSize(1050, 650)
        self.resize(1200, 780)

        self._settings = AppSettings.load()

        self._ssh_manager = SSHManager()
        self._sftp_manager: SFTPManager | None = None
        self._file_editor = RemoteFileEditor(self)

        self._transfer_manager = TransferManager(
            max_concurrent=self._settings.max_concurrent_transfers,
            parent=self,
        )

        self._last_connection_info: ConnectionInfo | None = None
        self._reconnecting = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(5000)
        self._health_timer.timeout.connect(self._check_connection_health)

        self._setup_ui()
        self._setup_menubar()
        self._setup_logging()
        self._connect_signals()

        self._ssh_manager.set_host_key_callback(self._on_verify_host_key)
        self._apply_theme_and_titlebar(self._settings.theme)

    def _setup_menubar(self):
        """Configure la barre de menus supérieure (Fichier, Affichage, Aide)."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Fichier")

        settings_action = QAction("⚙️ &Préférences...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("&Affichage")

        self._theme_action = QAction(
            "☀️ Basculer vers Thème Clair" if self._settings.theme == "dark" else "🌙 Basculer vers Thème Sombre",
            self,
        )
        self._theme_action.setShortcut("F10")
        self._theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self._theme_action)

        help_menu = menubar.addMenu("&Aide")

        about_action = QAction("&À propos de FileDrop", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _open_settings(self):
        """Ouvre le dialogue de configuration des paramètres."""
        dialog = SettingsDialog(self._settings, self)
        dialog.settings_applied.connect(self._on_settings_updated)
        dialog.exec()

    def _on_settings_updated(self):
        """Appelé quand les paramètres ont été modifiés."""
        self._apply_theme_and_titlebar(self._settings.theme)
        self._transfer_manager.set_max_concurrent(self._settings.max_concurrent_transfers)

    def _toggle_theme(self):
        """Bascule rapidement entre le thème sombre et clair."""
        new_theme = "light" if self._settings.theme == "dark" else "dark"
        self._settings.theme = new_theme
        self._settings.save()
        self._apply_theme_and_titlebar(new_theme)

    def _apply_theme_and_titlebar(self, theme_name: str):
        """Applique le thème QSS et synchronise la barre de titre native OS."""
        ThemeManager.apply_theme(theme_name)
        try:
            set_window_dark_mode(int(self.winId()), dark=(theme_name == "dark"))
        except Exception:
            pass
        self._update_theme_menu_label()

    def _update_theme_menu_label(self):
        """Met à jour l'intitulé du menu de bascule de thème."""
        if hasattr(self, "_theme_action"):
            if self._settings.theme == "dark":
                self._theme_action.setText("☀️ Basculer vers Thème Clair")
            else:
                self._theme_action.setText("🌙 Basculer vers Thème Sombre")

    def _show_about(self):
        """Affiche la boîte de dialogue À Propos."""
        QMessageBox.about(
            self,
            "À propos de FileDrop",
            f"<h2>FileDrop v{__version__}</h2>"
            "<p>Client SFTP graphique moderne, multiplateforme et sécurisé.</p>"
            "<p><b>Fonctionnalités :</b></p>"
            "<ul>"
            "<li>Double panneau d'exploration Local / Distant</li>"
            "<li>Transferts asynchrones multithreadés avec file d'attente intelligente</li>"
            "<li>Glisser-Déposer (Drag & Drop) visuel bidirectionnel et depuis l'OS</li>"
            "<li>Terminal SSH interactif intégré</li>"
            "<li>Édition de fichiers distants en direct</li>"
            "<li>Gestionnaire de favoris et clés SSH</li>"
            "<li>Thèmes Sombre et Clair dynamiques</li>"
            "</ul>"
            "<p>Développé avec <b>PyQt6</b> & <b>Paramiko</b>.</p>",
        )

    def _setup_ui(self):
        """Construit l'interface graphique."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        self._connection_bar = ConnectionBar()
        main_layout.addWidget(self._connection_bar)

        center_layout = QHBoxLayout()

        self._local_panel = LocalPanel()
        center_layout.addWidget(self._local_panel, stretch=1)

        self._transfer_buttons = TransferButtons()
        center_layout.addWidget(self._transfer_buttons)

        self._remote_panel = RemotePanel()
        center_layout.addWidget(self._remote_panel, stretch=1)

        center_widget = QWidget()
        center_widget.setLayout(center_layout)
        main_layout.addWidget(center_widget, stretch=3)

        self._bottom_tabs = QTabWidget()

        self._transfer_queue = TransferQueueWidget()
        self._bottom_tabs.addTab(self._transfer_queue, "Transferts")

        self._terminal_widget = TerminalWidget()
        self._bottom_tabs.addTab(self._terminal_widget, "Terminal SSH")

        self._log_widget = QTextEdit()
        self._log_widget.setReadOnly(True)
        self._log_widget.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: white; "
            "font-family: Consolas, monospace; font-size: 9pt; }"
        )
        self._bottom_tabs.addTab(self._log_widget, "Logs")

        main_layout.addWidget(self._bottom_tabs, stretch=1)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Prêt — Non connecté")

    def _setup_logging(self):
        """Configure le logging vers le widget de logs."""
        handler = LogHandler(self._log_widget)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def _connect_signals(self):
        """Connecte les signaux entre les composants."""
        self._connection_bar.connect_requested.connect(self._on_connect)
        self._connection_bar.disconnect_requested.connect(self._on_disconnect)

        self._transfer_buttons.upload_requested.connect(self._on_upload)
        self._transfer_buttons.download_requested.connect(self._on_download)
        self._local_panel.upload_requested.connect(self._on_upload_paths)
        self._remote_panel.download_requested.connect(self._on_download_entries)
        self._remote_panel.drop_upload_requested.connect(self._on_drop_upload)
        self._local_panel.drop_download_requested.connect(self._on_drop_download)

        self._transfer_queue.cancel_requested.connect(self._transfer_manager.cancel_transfer)

        self._remote_panel.edit_requested.connect(self._on_edit_remote_file)
        self._file_editor.upload_needed.connect(self._on_remote_file_modified)

        self._transfer_manager.task_added.connect(self._on_task_added)
        self._transfer_manager.task_updated.connect(self._transfer_queue.update_task)
        self._transfer_manager.task_finished.connect(self._on_task_finished)
        self._transfer_manager.queue_changed.connect(self._on_queue_changed)

    def _on_verify_host_key(self, hostname: str, key_type: str, fingerprint: str) -> bool:
        """Demande confirmation à l'utilisateur lors de la première connexion à un serveur."""
        reply = QMessageBox.warning(
            self,
            "Authenticité du serveur inconnue",
            f"L'authenticité de l'hôte distant '{hostname}' ne peut pas être établie.\n\n"
            f"Type de clé : {key_type}\n"
            f"Empreinte : {fingerprint}\n\n"
            "Voulez-vous approuver cette clé et vous connecter en toute sécurité ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _on_connect(self, connection_info: ConnectionInfo):
        """Établit la connexion SSH/SFTP et démarre les sous-systèmes."""
        try:
            self._ssh_manager.connect(
                connection_info,
                timeout=self._settings.connection_timeout,
                keepalive_interval=self._settings.keepalive_interval,
            )
            sftp_client = self._ssh_manager.open_sftp()
            self._sftp_manager = SFTPManager(sftp_client)

            home = self._sftp_manager.get_home_directory()
            self._sftp_manager.change_directory(home)
            self._remote_panel.set_sftp_manager(self._sftp_manager)
            self._remote_panel.refresh()

            self._transfer_manager.set_transport(self._ssh_manager.transport)

            try:
                channel = self._ssh_manager.invoke_shell()
                self._terminal_widget.start_session(channel)
            except Exception as e:
                logger.warning("Impossible d'ouvrir le terminal SSH : %s", e)

            self._connection_bar.set_connected(True)
            self._transfer_buttons.set_enabled(True)
            self._last_connection_info = connection_info
            self._reconnect_attempts = 0
            self._health_timer.start()

            self._status_bar.showMessage(f"Connecté à {connection_info.display_name}")
            logger.info("Connexion établie avec %s", connection_info.display_name)

        except Exception as e:
            logger.error("Échec de connexion : %s", e)
            self._status_bar.showMessage(f"Erreur : {e}")
            QMessageBox.critical(self, "Erreur de connexion", str(e))

    def _on_disconnect(self):
        """Ferme proprement la connexion et nettoie les sessions."""
        self._health_timer.stop()
        self._reconnecting = False

        self._transfer_manager.cancel_all()

        self._terminal_widget.stop_session()
        self._file_editor.cleanup()

        if self._sftp_manager:
            self._sftp_manager.close()
            self._sftp_manager = None

        self._ssh_manager.disconnect()
        self._transfer_manager.set_transport(None)
        self._remote_panel.clear()
        self._connection_bar.set_connected(False)
        self._transfer_buttons.set_enabled(False)
        self._status_bar.showMessage("Déconnecté")

    def _check_connection_health(self):
        """Surveille la santé du transport SSH et tente une reconnexion en cas de coupure."""
        if not self._connection_bar.is_connected or self._reconnecting:
            return

        if not self._ssh_manager.is_connected:
            self._handle_unexpected_disconnect()

    def _handle_unexpected_disconnect(self):
        """Déclenche la tentative de reconnexion automatique."""
        self._reconnecting = True
        self._reconnect_attempts += 1
        logger.warning(
            "Connexion perdue ! Tentative de reconnexion %d/%d...",
            self._reconnect_attempts,
            self._max_reconnect_attempts,
        )
        self._status_bar.showMessage(
            f"Connexion perdue — Reconnexion auto ({self._reconnect_attempts}/{self._max_reconnect_attempts})..."
        )

        if self._last_connection_info and self._reconnect_attempts <= self._max_reconnect_attempts:
            QTimer.singleShot(2000, self._perform_auto_reconnect)
        else:
            logger.error("Nombre maximal de tentatives de reconnexion atteint.")
            self._on_disconnect()
            QMessageBox.warning(
                self,
                "Connexion perdue",
                "La connexion avec le serveur distant a été interrompue.",
            )

    def _perform_auto_reconnect(self):
        """Exécute la reconnexion automatique."""
        if not self._last_connection_info:
            return
        try:
            self._ssh_manager.connect(
                self._last_connection_info,
                timeout=self._settings.connection_timeout,
                keepalive_interval=self._settings.keepalive_interval,
            )
            sftp_client = self._ssh_manager.open_sftp()
            self._sftp_manager = SFTPManager(sftp_client)
            self._remote_panel.set_sftp_manager(self._sftp_manager)
            self._remote_panel.refresh()

            self._transfer_manager.set_transport(self._ssh_manager.transport)

            try:
                channel = self._ssh_manager.invoke_shell()
                self._terminal_widget.start_session(channel)
            except Exception:
                pass

            self._reconnecting = False
            self._reconnect_attempts = 0
            self._status_bar.showMessage(f"Reconnecté à {self._last_connection_info.display_name}")
            logger.info("Reconnexion automatique réussie !")

        except Exception as e:
            logger.warning("Échec de la tentative de reconnexion : %s", e)
            self._reconnecting = False
            if self._reconnect_attempts < self._max_reconnect_attempts:
                self._handle_unexpected_disconnect()
            else:
                self._on_disconnect()

    def _on_edit_remote_file(self, entry):
        """Télécharge un fichier distant et l'ouvre dans l'éditeur système par défaut."""
        if not self._sftp_manager:
            return
        try:
            self._status_bar.showMessage(f"Ouverture de {entry.filename} pour édition...")
            self._file_editor.open_remote_file(self._sftp_manager, entry.filepath)
        except Exception as e:
            logger.error("Erreur ouverture pour édition %s : %s", entry.filepath, e)
            QMessageBox.warning(self, "Erreur d'édition", f"Impossible d'ouvrir le fichier : {e}")

    def _on_remote_file_modified(self, local_path: str, remote_path: str):
        """Re-upload automatiquement le fichier distant après modification locale."""
        logger.info("Sauvegarde détectée, re-upload automatique de %s", remote_path)
        self._transfer_manager.start_transfer(
            local_path=local_path,
            remote_path=remote_path,
            direction=TransferDirection.UPLOAD,
        )

    def _on_task_added(self, task: TransferTask):
        """Ajoute la tâche au widget de file d'attente et bascule l'onglet."""
        self._transfer_queue.add_task(task)
        self._bottom_tabs.setCurrentWidget(self._transfer_queue)

    def _on_task_finished(self, task: TransferTask):
        """Met à jour le widget et rafraîchit le panneau distant après un upload réussi."""
        self._transfer_queue.update_task(task)
        if task.status == TransferStatus.COMPLETED and task.direction == TransferDirection.UPLOAD:
            self._remote_panel.refresh()

    def _on_queue_changed(self, active: int, pending: int):
        """Met à jour la barre de statut avec les compteurs de transferts."""
        if active == 0 and pending == 0:
            if self._ssh_manager.is_connected:
                self._status_bar.showMessage("Connecté — Aucun transfert en cours")
            else:
                self._status_bar.showMessage("Prêt — Non connecté")
        else:
            self._status_bar.showMessage(
                f"Transferts : {active} actif(s), {pending} en attente"
            )

    def _on_upload(self):
        """Déclenche l'envoi des éléments sélectionnés dans le panneau local."""
        selected = self._local_panel.get_selected_paths()
        if not selected:
            self._status_bar.showMessage("Sélectionnez des fichiers locaux à envoyer")
            return
        self._on_upload_paths(selected)

    def _on_download(self):
        """Déclenche le téléchargement des éléments sélectionnés dans le panneau distant."""
        selected = self._remote_panel.get_selected_entries()
        if not selected:
            self._status_bar.showMessage("Sélectionnez des fichiers distants à télécharger")
            return
        self._on_download_entries(selected)

    def _on_upload_paths(self, paths: list):
        """Délègue l'upload au gestionnaire de transferts."""
        if not self._ssh_manager.is_connected or not self._sftp_manager:
            self._status_bar.showMessage("Non connecté")
            return
        self._transfer_manager.upload_paths(paths, self._sftp_manager.current_path, self._sftp_manager)

    def _on_download_entries(self, entries: list):
        """Délègue le download au gestionnaire de transferts."""
        if not self._ssh_manager.is_connected:
            return
        self._transfer_manager.download_entries(entries, self._local_panel.current_path, self._sftp_manager)

    def _on_drop_upload(self, local_paths: list[str], remote_target_dir: str):
        """Gère le dépôt de fichiers locaux vers un répertoire distant."""
        if not self._ssh_manager.is_connected or not self._sftp_manager:
            self._status_bar.showMessage("Non connecté")
            return
        target_dir = remote_target_dir if remote_target_dir else self._sftp_manager.current_path
        self._transfer_manager.upload_paths(local_paths, target_dir, self._sftp_manager)

    def _on_drop_download(self, entries_data: list[dict], local_target_dir: str):
        """Gère le dépôt d'éléments distants vers un répertoire local."""
        if not self._ssh_manager.is_connected:
            return
        target_dir = local_target_dir if local_target_dir else self._local_panel.current_path

        for entry_data in entries_data:
            remote_path = entry_data["path"]
            is_dir = entry_data["is_dir"]
            filename = remote_path.rsplit("/", 1)[-1]

            if is_dir:
                self._transfer_manager.download_directory(remote_path, target_dir, self._sftp_manager)
            else:
                self._transfer_manager.start_transfer(
                    os.path.join(target_dir, filename), remote_path, TransferDirection.DOWNLOAD
                )

    def closeEvent(self, event):
        """Ferme proprement l'application en attendant les workers."""
        self._on_disconnect()
        self._transfer_manager.wait_for_workers(1000)
        super().closeEvent(event)
