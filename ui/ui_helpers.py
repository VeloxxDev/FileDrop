"""Utilitaires graphiques partagés pour l'interface utilisateur de FileDrop.

Évite la duplication de code entre le panneau local et le panneau distant :
- Génération d'aperçu pour le Drag & Drop
- Configuration des raccourcis clavier
- Boîtes de dialogue de confirmation
"""

from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QBrush,
    QIcon,
    QAction,
)


def create_drag_preview(
    parent: QWidget,
    icon: QIcon | str,
    text: str,
    count: int = 1,
) -> tuple[QPixmap, QPoint]:
    """Construit une vignette semi-transparente avec icône et libellé pour le glisser-déposer."""
    fm = parent.fontMetrics()
    display_text = f"{text} (+{count-1})" if count > 1 else text
    elided_text = fm.elidedText(display_text, Qt.TextElideMode.ElideRight, 160)

    text_width = fm.horizontalAdvance(elided_text) + 16
    text_height = fm.height() + 8
    icon_size = 48

    width = max(icon_size, text_width) + 12
    height = icon_size + text_height + 10

    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if isinstance(icon, QIcon):
        icon_pix = icon.pixmap(icon_size, icon_size)
        painter.drawPixmap((width - icon_size) // 2, 0, icon_pix)
    else:
        painter.setPen(QColor(0, 0, 0))
        font = painter.font()
        font.setPointSize(28)
        painter.setFont(font)
        painter.drawText(
            QRect(0, 0, width, icon_size),
            Qt.AlignmentFlag.AlignCenter,
            str(icon),
        )

    painter.setBrush(QBrush(QColor(0, 120, 215, 240)))
    painter.setPen(Qt.PenStyle.NoPen)
    bg_rect = QRect(
        (width - text_width) // 2,
        icon_size + 2,
        text_width,
        text_height,
    )
    painter.drawRoundedRect(bg_rect, 6, 6)

    painter.setFont(parent.font())
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, elided_text)

    painter.end()

    hotspot = QPoint(pixmap.width() // 2, pixmap.height() // 2)
    return pixmap, hotspot


def setup_panel_shortcuts(
    panel: QWidget,
    on_delete,
    on_rename,
    on_refresh,
) -> None:
    """Configure de manière uniforme les raccourcis F2, Suppr et F5 sur un panneau.

    Utilise Qt.ShortcutContext.WidgetWithChildrenShortcut pour éviter tout conflit
    entre les deux panneaux.
    """
    del_action = QAction(panel)
    del_action.setShortcut("Del")
    del_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    del_action.triggered.connect(on_delete)
    panel.addAction(del_action)

    ren_action = QAction(panel)
    ren_action.setShortcut("F2")
    ren_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    ren_action.triggered.connect(on_rename)
    panel.addAction(ren_action)

    ref_action = QAction(panel)
    ref_action.setShortcut("F5")
    ref_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    ref_action.triggered.connect(on_refresh)
    panel.addAction(ref_action)


def confirm_deletion_dialog(
    parent: QWidget,
    count: int,
    sample_name: str,
    is_remote: bool = False,
) -> bool:
    """Demande une confirmation utilisateur avant la suppression d'un ou plusieurs éléments."""
    location = " du serveur" if is_remote else ""
    if count > 1:
        msg = f"Supprimer {count} éléments{location} ?"
    else:
        msg = f"Supprimer '{sample_name}'{location} ?"

    reply = QMessageBox.question(
        parent,
        "Confirmer la suppression",
        msg,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes
