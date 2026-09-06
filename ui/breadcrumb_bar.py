"""Barre de chemin cliquable de type fil d'Ariane (Breadcrumb) comme dans Windows.

Permet de cliquer directement sur n'importe quel dossier parent du chemin
ou de cliquer dans la zone vide pour saisir/coller un chemin complet.
"""

import os
import sys
from pathlib import Path, PurePosixPath

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QTimer


class BreadcrumbBar(QWidget):
    """Barre de navigation par fil d'Ariane cliquable avec mode saisie directe.

    Signals:
        path_selected(str): Émis lorsqu'un chemin est cliqué ou validé.
    """

    path_selected = pyqtSignal(str)

    def __init__(self, is_remote: bool = False, parent=None):
        super().__init__(parent)
        self._is_remote = is_remote
        self._current_path = ""
        self._scroll_area = None
        self._crumb_container = None
        self._edit_input = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        self._stack.setObjectName("breadcrumbContainer")

        self._crumb_container = QWidget()
        self._crumb_layout = QHBoxLayout(self._crumb_container)
        self._crumb_layout.setContentsMargins(4, 2, 4, 2)
        self._crumb_layout.setSpacing(1)
        self._crumb_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Masque les ascenseurs pour un défilement horizontal compact sans encombrement visuel
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll_area.setWidget(self._crumb_container)
        self._scroll_area.setObjectName("breadcrumbScrollArea")

        self._stack.addWidget(self._scroll_area)

        self._edit_input = QLineEdit()
        self._edit_input.returnPressed.connect(self._on_edit_validated)
        self._stack.addWidget(self._edit_input)

        self._scroll_area.installEventFilter(self)
        self._crumb_container.installEventFilter(self)
        self._edit_input.installEventFilter(self)

        main_layout.addWidget(self._stack)

        # Aligne la hauteur sur les champs de saisie standards pour l'homogénéité visuelle
        self.setMaximumHeight(28)

    def set_path(self, path: str):
        """Régénère les boutons de navigation pour représenter le chemin donné."""
        self._current_path = path.strip()
        self._edit_input.setText(self._current_path)

        while self._crumb_layout.count() > 0:
            item = self._crumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._current_path:
            return

        segments = self._parse_path_segments(self._current_path)

        for i, (label, seg_path) in enumerate(segments):
            btn = QPushButton(label)
            btn.setProperty("class", "breadcrumb-segment")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, p=seg_path: self.path_selected.emit(p))
            self._crumb_layout.addWidget(btn)

            if i < len(segments) - 1:
                sep = QLabel("›")
                sep.setProperty("class", "breadcrumb-separator")
                sep.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
                self._crumb_layout.addWidget(sep)

        # Laisse une zone cliquable vide à droite permettant de basculer en saisie libre
        self._crumb_layout.addStretch()

        self._stack.setCurrentIndex(0)

        # Défile vers l'extrémité droite pour révéler le dossier le plus profond
        QTimer.singleShot(50, lambda: self._scroll_area.horizontalScrollBar().setValue(
            self._scroll_area.horizontalScrollBar().maximum()
        ))

    def _parse_path_segments(self, path: str) -> list[tuple[str, str]]:
        """Décompose le chemin en segments sous forme (libellé, chemin_cumulé)."""
        segments = []

        if self._is_remote:
            clean_path = PurePosixPath(path)
            parts = clean_path.parts

            if not parts or parts == ("/",):
                return [("/", "/")]

            accum = "/"
            segments.append(("/", "/"))

            for part in parts:
                if part == "/":
                    continue
                accum = str(PurePosixPath(accum) / part)
                segments.append((part, accum))

        else:
            if sys.platform == "win32":
                p = Path(path).resolve()
                drive = p.drive
                if drive:
                    accum = drive + "\\"
                    segments.append((f"💾 {drive}", accum))
                    parts = p.parts[1:]
                else:
                    parts = p.parts
                    accum = ""

                for part in parts:
                    accum = os.path.join(accum, part)
                    segments.append((part, accum))
            else:
                p = Path(path).resolve()
                accum = "/"
                segments.append(("/", "/"))
                for part in p.parts[1:]:
                    accum = os.path.join(accum, part)
                    segments.append((part, accum))

        return segments

    def switch_to_edit_mode(self):
        """Affiche le champ de saisie directe avec le chemin actuel pré-sélectionné."""
        self._edit_input.setText(self._current_path)
        self._stack.setCurrentIndex(1)
        self._edit_input.setFocus()
        self._edit_input.selectAll()

    def _on_edit_validated(self):
        """Émet le nouveau chemin saisi et rétablit l'affichage du fil d'Ariane."""
        new_path = self._edit_input.text().strip()
        if new_path:
            self.path_selected.emit(new_path)
        self._stack.setCurrentIndex(0)

    def eventFilter(self, watched, event):
        """Gère la bascule vers le mode saisie ou l'annulation selon les clics et raccourcis."""
        if not self._crumb_container or not self._edit_input:
            return super().eventFilter(watched, event)

        # Reproduit l'ergonomie de l'explorateur Windows en ouvrant l'édition sur un clic du fond
        if (watched in (self._crumb_container, self._scroll_area)
                and event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton):
            child = self._crumb_container.childAt(event.pos())
            if not isinstance(child, QPushButton):
                self.switch_to_edit_mode()
                return True

        if watched == self._edit_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._stack.setCurrentIndex(0)
                return True

        if watched == self._edit_input and event.type() == QEvent.Type.FocusOut:
            self._stack.setCurrentIndex(0)

        return super().eventFilter(watched, event)
