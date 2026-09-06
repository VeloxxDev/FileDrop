"""Widget de file d'attente des transferts avec annulation."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QProgressBar,
    QPushButton,
    QHeaderView,
)
from PyQt6.QtCore import pyqtSignal

from models.transfer_task import TransferTask, TransferDirection, TransferStatus
from utils.formatters import format_size


class TransferQueueWidget(QWidget):
    """Affiche la file d'attente des transferts avec barres de progression.

    Signals:
        cancel_requested(task): L'utilisateur veut annuler un transfert.
    """

    cancel_requested = pyqtSignal(TransferTask)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: dict[int, tuple[QTreeWidgetItem, TransferTask]] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(
            ["Direction", "Fichier", "Taille", "Progression", "Statut"]
        )
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 200)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._tree)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self._cancel_button = QPushButton("Annuler")
        self._cancel_button.setToolTip("Annuler le transfert sélectionné")
        self._cancel_button.setFixedWidth(100)
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        buttons_layout.addWidget(self._cancel_button)

        self._clear_button = QPushButton("Nettoyer")
        self._clear_button.setToolTip("Supprimer les transferts terminés")
        self._clear_button.setFixedWidth(100)
        self._clear_button.clicked.connect(self.remove_completed)
        buttons_layout.addWidget(self._clear_button)

        layout.addLayout(buttons_layout)

    def add_task(self, task: TransferTask):
        """Insère une nouvelle tâche dans le tableau avec sa barre de progression."""
        item = QTreeWidgetItem()
        direction_icon = "⬆️" if task.direction == TransferDirection.UPLOAD else "⬇️"
        item.setText(0, direction_icon)
        item.setText(1, task.filename)
        item.setText(2, format_size(task.file_size))
        item.setText(4, task.status.name)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)

        self._tree.addTopLevelItem(item)
        self._tree.setItemWidget(item, 3, progress_bar)

        self._tasks[id(task)] = (item, task)

    def update_task(self, task: TransferTask):
        """Actualise la jauge et l'état affiché pour la tâche correspondante."""
        entry = self._tasks.get(id(task))
        if entry:
            item, _ = entry
            progress_bar = self._tree.itemWidget(item, 3)
            if isinstance(progress_bar, QProgressBar):
                progress_bar.setValue(task.progress_percent)
            item.setText(2, format_size(task.file_size))
            item.setText(4, task.status.name)

    def _on_cancel_clicked(self):
        """Émet une demande d'annulation pour la tâche sélectionnée."""
        selected = self._tree.currentItem()
        if selected is None:
            return
        for task_id, (item, task) in self._tasks.items():
            if item is selected and task.status in (
                TransferStatus.QUEUED, TransferStatus.IN_PROGRESS
            ):
                self.cancel_requested.emit(task)
                break

    def remove_completed(self):
        """Retire du tableau toutes les tâches achevées, échouées ou annulées."""
        to_remove = []
        for task_id, (item, task) in self._tasks.items():
            if task.status in (
                TransferStatus.COMPLETED,
                TransferStatus.CANCELLED,
                TransferStatus.FAILED,
            ):
                index = self._tree.indexOfTopLevelItem(item)
                if index >= 0:
                    self._tree.takeTopLevelItem(index)
                to_remove.append(task_id)
        for task_id in to_remove:
            del self._tasks[task_id]
