"""Panneau d'exploration du système de fichiers distant (SFTP).

Utilise QTreeWidget peuplé manuellement via SFTPManager, avec menu contextuel et Drag & Drop personnalisé.
"""

import logging
import json
from pathlib import PurePosixPath

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QPushButton,
    QLabel,
    QHeaderView,
    QMenu,
    QInputDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDrag

from core.sftp_manager import SFTPManager, RemoteFileInfo
from utils.formatters import format_size
from ui.ui_helpers import (
    create_drag_preview,
    setup_panel_shortcuts,
    confirm_deletion_dialog,
)
from ui.breadcrumb_bar import BreadcrumbBar
from PyQt6.QtWidgets import QStyle

logger = logging.getLogger(__name__)


class RemoteTreeWidget(QTreeWidget):
    """QTreeWidget personnalisé pour gérer Drag & Drop SFTP et l'aperçu du Drag."""

    drop_upload_requested = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)

    def mimeTypes(self):
        return ["application/x-filedrop-remote"]

    def mimeData(self, items):
        mime = QMimeData()
        entries = []
        for item in items:
            entry = item.data(0, Qt.ItemDataRole.UserRole)
            if entry:
                entries.append({"path": entry.filepath, "is_dir": entry.is_dir})

        json_data = json.dumps(entries).encode("utf-8")
        mime.setData("application/x-filedrop-remote", json_data)
        return mime

    def startDrag(self, supportedActions):
        """Génère la vignette personnalisée et le payload MIME pour le glisser-déposer distant."""
        items = self.selectedItems()
        if not items:
            return

        drag = QDrag(self)
        drag.setMimeData(self.mimeData(items))

        first_item = items[0]
        icon = first_item.icon(0)
        text = first_item.text(0)

        count = len(items)
        pixmap, hotspot = create_drag_preview(self, icon, text, count)
        drag.setPixmap(pixmap)
        drag.setHotSpot(hotspot)

        drag.exec(supportedActions, Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            local_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]

            target_item = self.itemAt(event.position().toPoint())
            target_dir = ""
            if target_item:
                entry = target_item.data(0, Qt.ItemDataRole.UserRole)
                if entry and entry.is_dir:
                    target_dir = entry.filepath

            if local_paths:
                self.drop_upload_requested.emit(local_paths, target_dir)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class RemotePanel(QWidget):
    """Panneau droit — explorateur de fichiers distant via SFTP."""

    download_requested = pyqtSignal(list)
    drop_upload_requested = pyqtSignal(list, str)
    edit_requested = pyqtSignal(RemoteFileInfo)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sftp_manager: SFTPManager | None = None
        self._show_hidden = False
        self._setup_ui()
        setup_panel_shortcuts(
            panel=self,
            on_delete=lambda: self._delete_items(self.get_selected_entries()),
            on_rename=self._on_rename_shortcut,
            on_refresh=self.refresh,
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("🌐 Distant"))

        path_layout = QHBoxLayout()
        self._breadcrumb = BreadcrumbBar(is_remote=True)
        self._breadcrumb.path_selected.connect(self._navigate_to)
        path_layout.addWidget(self._breadcrumb, stretch=1)

        self._hidden_btn = QPushButton("👁")
        self._hidden_btn.setCheckable(True)
        self._hidden_btn.setFixedWidth(32)
        self._hidden_btn.setToolTip("Afficher / Masquer les fichiers cachés")
        self._hidden_btn.setEnabled(False)
        self._hidden_btn.clicked.connect(self._toggle_hidden)
        path_layout.addWidget(self._hidden_btn)

        self._up_button = QPushButton("⬆")
        self._up_button.setFixedWidth(32)
        self._up_button.setToolTip("Dossier parent")
        self._up_button.setEnabled(False)
        self._up_button.clicked.connect(self._go_up)
        path_layout.addWidget(self._up_button)

        self._refresh_button = QPushButton("🔄")
        self._refresh_button.setFixedWidth(32)
        self._refresh_button.setToolTip("Rafraîchir")
        self._refresh_button.setEnabled(False)
        self._refresh_button.clicked.connect(self.refresh)
        path_layout.addWidget(self._refresh_button)

        layout.addLayout(path_layout)

        self._tree = RemoteTreeWidget()
        self._tree.setHeaderLabels(["Nom", "Taille", "Date", "Permissions"])
        self._tree.setSortingEnabled(True)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self._tree.itemDoubleClicked.connect(self._on_double_click)

        self._tree.drop_upload_requested.connect(self.drop_upload_requested.emit)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._tree)

    def _on_rename_shortcut(self):
        selected = self.get_selected_entries()
        if len(selected) == 1:
            self._rename_item(selected[0])

    def _toggle_hidden(self, checked: bool):
        self._show_hidden = checked
        self.refresh()

    def _show_context_menu(self, position):
        if not self._sftp_manager:
            return

        menu = QMenu(self)
        selected = self.get_selected_entries()

        if selected:
            download_action = menu.addAction("← Télécharger")
            download_action.triggered.connect(lambda: self.download_requested.emit(selected))
            menu.addSeparator()

            if len(selected) == 1:
                if not selected[0].is_dir:
                    edit_action = menu.addAction("✏️ Éditer le fichier")
                    edit_action.triggered.connect(lambda: self.edit_requested.emit(selected[0]))

                rename_action = menu.addAction("Renommer\tF2")
                rename_action.triggered.connect(lambda: self._rename_item(selected[0]))

            delete_action = menu.addAction("Supprimer\tSuppr")
            delete_action.triggered.connect(lambda: self._delete_items(selected))
            menu.addSeparator()

        new_folder_action = menu.addAction("Nouveau dossier")
        new_folder_action.triggered.connect(self._create_folder)

        refresh_action = menu.addAction("Rafraîchir\tF5")
        refresh_action.triggered.connect(self.refresh)

        menu.exec(self._tree.viewport().mapToGlobal(position))

    def _rename_item(self, entry: RemoteFileInfo):
        """Invite à renommer un fichier ou dossier distant."""
        new_name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=entry.filename)
        if ok and new_name and new_name != entry.filename:
            parent = str(PurePosixPath(entry.filepath).parent)
            new_path = str(PurePosixPath(parent) / new_name)
            try:
                self._sftp_manager.rename(entry.filepath, new_path)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de renommer : {e}")

    def _delete_items(self, entries: list[RemoteFileInfo]):
        """Supprime les éléments distants sélectionnés après confirmation."""
        if not entries:
            return
        if confirm_deletion_dialog(self, len(entries), entries[0].filename, is_remote=True):
            for entry in entries:
                try:
                    if entry.is_dir:
                        self._delete_directory_recursive(entry.filepath)
                    else:
                        self._sftp_manager.remove(entry.filepath)
                except Exception as e:
                    logger.error("Erreur suppression %s : %s", entry.filepath, e)
            self.refresh()

    def _delete_directory_recursive(self, path: str):
        """Supprime récursivement les sous-dossiers et fichiers avant de retirer le dossier."""
        try:
            entries = self._sftp_manager.list_directory(path)
            for entry in entries:
                if entry.is_dir:
                    self._delete_directory_recursive(entry.filepath)
                else:
                    self._sftp_manager.remove(entry.filepath)
            self._sftp_manager.rmdir(path)
        except Exception as e:
            logger.error("Erreur suppression récursive %s : %s", path, e)

    def _create_folder(self):
        """Crée un répertoire distant à l'emplacement actuel."""
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
        if ok and name:
            new_path = str(PurePosixPath(self._sftp_manager.current_path) / name)
            try:
                self._sftp_manager.mkdir(new_path)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de créer le dossier : {e}")

    def set_sftp_manager(self, sftp_manager: SFTPManager):
        """Associe le client SFTP actif et active les boutons de navigation."""
        self._sftp_manager = sftp_manager
        self._up_button.setEnabled(True)
        self._refresh_button.setEnabled(True)
        self._hidden_btn.setEnabled(True)

    def refresh(self):
        """Recharge et affiche le contenu du répertoire distant courant."""
        if not self._sftp_manager:
            return

        self._tree.clear()
        self._breadcrumb.set_path(self._sftp_manager.current_path)

        style = self.style()
        dir_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        link_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon)

        try:
            entries = self._sftp_manager.list_directory()
            for entry in entries:
                if not self._show_hidden and entry.filename.startswith("."):
                    continue

                item = QTreeWidgetItem()
                if entry.is_dir:
                    item.setIcon(0, dir_icon)
                elif entry.is_link:
                    item.setIcon(0, link_icon)
                else:
                    item.setIcon(0, file_icon)

                item.setText(0, entry.filename)
                item.setText(1, format_size(entry.size) if not entry.is_dir else "")
                item.setText(2, entry.mtime_str)
                item.setText(3, entry.permissions_str)
                item.setData(0, Qt.ItemDataRole.UserRole, entry)
                self._tree.addTopLevelItem(item)

        except Exception as e:
            logger.error("Erreur listing distant : %s", e)

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        entry: RemoteFileInfo = item.data(0, Qt.ItemDataRole.UserRole)
        if entry and entry.is_dir:
            self._navigate_to(entry.filepath)

    def _navigate_to(self, path: str):
        """Navigue vers un dossier distant et actualise l'affichage."""
        if self._sftp_manager and path:
            try:
                self._sftp_manager.change_directory(path)
                self.refresh()
            except Exception as e:
                logger.error("Impossible de naviguer vers %s : %s", path, e)
                QMessageBox.warning(self, "Erreur", f"Impossible d'accéder au dossier : {e}")

    def _go_up(self):
        """Remonte au dossier parent sur le serveur distant."""
        if self._sftp_manager:
            current = self._sftp_manager.current_path
            parent = str(PurePosixPath(current).parent)
            if parent != current:
                self._navigate_to(parent)

    def clear(self):
        """Réinitialise l'affichage et verrouille les commandes lors de la déconnexion."""
        self._tree.clear()
        self._breadcrumb.set_path("")
        self._up_button.setEnabled(False)
        self._refresh_button.setEnabled(False)
        self._hidden_btn.setEnabled(False)
        self._sftp_manager = None

    def get_selected_entries(self) -> list[RemoteFileInfo]:
        """Retourne la liste des éléments distants sélectionnés."""
        entries = []
        for item in self._tree.selectedItems():
            entry = item.data(0, Qt.ItemDataRole.UserRole)
            if entry:
                entries.append(entry)
        return entries
