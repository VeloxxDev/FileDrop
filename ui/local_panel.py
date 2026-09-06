"""Panneau d'exploration du système de fichiers local.

Utilise QFileSystemModel natif de Qt avec menu contextuel et Drag & Drop personnalisé.
"""

import os
import shutil
import logging
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeView,
    QLineEdit,
    QPushButton,
    QLabel,
    QHeaderView,
    QMenu,
    QInputDialog,
    QMessageBox,
)
from PyQt6.QtCore import QDir, QModelIndex, QUrl, pyqtSignal, Qt
from PyQt6.QtGui import QFileSystemModel, QDesktopServices, QDrag

from ui.ui_helpers import (
    create_drag_preview,
    setup_panel_shortcuts,
    confirm_deletion_dialog,
)
from ui.breadcrumb_bar import BreadcrumbBar

logger = logging.getLogger(__name__)


class LocalTreeView(QTreeView):
    """QTreeView personnalisé pour gérer le Drop et l'aperçu du Drag."""

    drop_download_requested = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

    def startDrag(self, supportedActions):
        """Génère la vignette personnalisée pour le glisser-déposer local."""
        indexes = self.selectedIndexes()
        if not indexes:
            return

        col0_indexes = [idx for idx in indexes if idx.column() == 0]
        if not col0_indexes:
            return

        mime_data = self.model().mimeData(col0_indexes)
        if not mime_data:
            return

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        first_index = col0_indexes[0]
        icon = self.model().data(first_index, Qt.ItemDataRole.DecorationRole)
        text = self.model().data(first_index, Qt.ItemDataRole.DisplayRole)
        count = len(col0_indexes)

        pixmap, hotspot = create_drag_preview(self, icon, str(text), count)
        drag.setPixmap(pixmap)
        drag.setHotSpot(hotspot)

        drag.exec(supportedActions, Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-filedrop-remote"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-filedrop-remote"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-filedrop-remote"):
            try:
                raw_bytes = event.mimeData().data("application/x-filedrop-remote").data()
                data = raw_bytes.decode("utf-8")
                entries = json.loads(data)

                if not isinstance(entries, list):
                    return
                valid_entries = [
                    e for e in entries
                    if isinstance(e, dict) and "path" in e and "is_dir" in e
                ]
            except Exception as e:
                logger.warning("Payload de drag & drop invalide : %s", e)
                return

            index = self.indexAt(event.position().toPoint())
            model = self.model()
            if index.isValid() and os.path.isdir(model.filePath(index)):
                target_dir = model.filePath(index)
            else:
                target_dir = ""

            if valid_entries:
                self.drop_download_requested.emit(valid_entries, target_dir)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class LocalPanel(QWidget):
    """Panneau gauche — explorateur de fichiers local."""

    upload_requested = pyqtSignal(list)
    drop_download_requested = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = str(Path.home())
        self._setup_ui()
        setup_panel_shortcuts(
            panel=self,
            on_delete=lambda: self._delete_items(self.get_selected_paths()),
            on_rename=self._on_rename_shortcut,
            on_refresh=lambda: self._navigate_to(self._current_path),
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("💻 Local"))

        path_layout = QHBoxLayout()
        self._breadcrumb = BreadcrumbBar(is_remote=False)
        self._breadcrumb.path_selected.connect(self._navigate_to)
        path_layout.addWidget(self._breadcrumb, stretch=1)

        self._hidden_btn = QPushButton("👁")
        self._hidden_btn.setCheckable(True)
        self._hidden_btn.setFixedWidth(32)
        self._hidden_btn.setToolTip("Afficher / Masquer les fichiers cachés")
        self._hidden_btn.clicked.connect(self._toggle_hidden)
        path_layout.addWidget(self._hidden_btn)

        self._up_button = QPushButton("⬆")
        self._up_button.setFixedWidth(32)
        self._up_button.setToolTip("Dossier parent")
        self._up_button.clicked.connect(self._go_up)
        path_layout.addWidget(self._up_button)

        layout.addLayout(path_layout)

        self._model = QFileSystemModel()
        self._model.setRootPath(self._current_path)
        self._breadcrumb.set_path(self._current_path)
        self._model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self._tree = LocalTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIndex(self._model.index(self._current_path))
        self._tree.setSortingEnabled(True)
        self._tree.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self._tree.doubleClicked.connect(self._on_double_click)

        self._tree.drop_download_requested.connect(self.drop_download_requested.emit)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._tree)

    def _on_rename_shortcut(self):
        selected = self.get_selected_paths()
        if len(selected) == 1:
            self._rename_item(selected[0])

    def _toggle_hidden(self, checked: bool):
        filters = QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
        if checked:
            filters |= QDir.Filter.Hidden
        self._model.setFilter(filters)

    def _show_context_menu(self, position):
        """Affiche le menu contextuel sur le clic droit selon la sélection active."""
        menu = QMenu(self)
        selected = self.get_selected_paths()

        if selected:
            upload_action = menu.addAction("→ Envoyer vers le serveur")
            upload_action.triggered.connect(lambda: self.upload_requested.emit(selected))
            menu.addSeparator()

            if len(selected) == 1:
                open_action = menu.addAction("Ouvrir")
                open_action.triggered.connect(lambda: self._open_file(selected[0]))
                rename_action = menu.addAction("Renommer\tF2")
                rename_action.triggered.connect(lambda: self._rename_item(selected[0]))

            delete_action = menu.addAction("Supprimer\tSuppr")
            delete_action.triggered.connect(lambda: self._delete_items(selected))
            menu.addSeparator()

        new_folder_action = menu.addAction("Nouveau dossier")
        new_folder_action.triggered.connect(self._create_folder)

        refresh_action = menu.addAction("Rafraîchir\tF5")
        refresh_action.triggered.connect(lambda: self._navigate_to(self._current_path))

        menu.exec(self._tree.viewport().mapToGlobal(position))

    def _open_file(self, path: str):
        """Lance l'application système par défaut pour ouvrir le fichier."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _rename_item(self, path: str):
        """Invite l'utilisateur à renommer l'élément local sélectionné."""
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            try:
                os.rename(path, new_path)
            except OSError as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de renommer : {e}")

    def _delete_items(self, paths: list[str]):
        """Supprime définitivement les fichiers ou dossiers locaux après confirmation."""
        if not paths:
            return
        if confirm_deletion_dialog(self, len(paths), os.path.basename(paths[0]), is_remote=False):
            for path in paths:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except OSError as e:
                    logger.error("Erreur suppression %s : %s", path, e)

    def _create_folder(self):
        """Crée un nouveau sous-dossier à l'emplacement courant."""
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
        if ok and name:
            new_path = os.path.join(self._current_path, name)
            try:
                os.makedirs(new_path, exist_ok=True)
            except OSError as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de créer le dossier : {e}")

    def _on_double_click(self, index: QModelIndex):
        path = self._model.filePath(index)
        if os.path.isdir(path):
            self._navigate_to(path)

    def _go_up(self):
        """Remonte d'un niveau dans l'arborescence des dossiers locaux."""
        parent = str(Path(self._current_path).parent)
        if parent != self._current_path:
            self._navigate_to(parent)

    def _navigate_to(self, path: str):
        """Positionne l'explorateur sur le répertoire spécifié et actualise la vue."""
        if not os.path.exists(path):
            return
        self._current_path = str(Path(path).resolve())
        self._breadcrumb.set_path(self._current_path)
        self._tree.setRootIndex(self._model.index(self._current_path))

    def get_selected_paths(self) -> list[str]:
        """Retourne la liste des chemins absolus actuellement sélectionnés."""
        return [
            self._model.filePath(index)
            for index in self._tree.selectionModel().selectedIndexes()
            if index.column() == 0
        ]

    @property
    def current_path(self) -> str:
        """Chemin absolu du dossier local actif."""
        return self._current_path
