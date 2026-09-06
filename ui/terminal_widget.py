"""Terminal SSH interactif intégré.

Utilise Paramiko invoke_shell() avec un QPlainTextEdit console
et un thread de lecture asynchrone non-bloquant.
"""

import logging
import re
import paramiko
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QLabel,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QTextCursor, QFont

logger = logging.getLogger(__name__)

ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class TerminalReceiver(QThread):
    """Thread dédié à la lecture asynchrone et non bloquante du canal SSH."""

    data_received = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, channel: paramiko.Channel, parent=None):
        super().__init__(parent)
        self._channel = channel
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running and self._channel and not self._channel.closed:
            try:
                if self._channel.recv_ready():
                    raw = self._channel.recv(2048)
                    if not raw:
                        break
                    text = raw.decode("utf-8", errors="replace")
                    self.data_received.emit(text)
                else:
                    self.msleep(15)
            except Exception as e:
                logger.debug("Fin du flux terminal : %s", e)
                break

        self.connection_lost.emit()


class ConsoleEdit(QPlainTextEdit):
    """Console textuelle transmettant les saisies utilisateur au canal SSH."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channel: paramiko.Channel | None = None
        self.setStyleSheet(
            "QPlainTextEdit { background-color: #121212; color: #00ff66; "
            "font-family: Consolas, 'Courier New', monospace; font-size: 10pt; "
            "border: none; padding: 4px; }"
        )
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

    def set_channel(self, channel: paramiko.Channel | None):
        self._channel = channel

    def keyPressEvent(self, event):
        if not self._channel or self._channel.closed:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()
        text = event.text()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                self._channel.send("\x03")
                return
            elif key == Qt.Key.Key_D:
                self._channel.send("\x04")
                return
            elif key == Qt.Key.Key_Z:
                self._channel.send("\x1a")
                return
            elif key == Qt.Key.Key_L:
                self._channel.send("\x0c")
                return

        match key:
            case Qt.Key.Key_Return | Qt.Key.Key_Enter:
                self._channel.send("\r")
            case Qt.Key.Key_Backspace:
                self._channel.send("\x08")
            case Qt.Key.Key_Tab:
                self._channel.send("\t")
            case Qt.Key.Key_Up:
                self._channel.send("\x1b[A")
            case Qt.Key.Key_Down:
                self._channel.send("\x1b[B")
            case Qt.Key.Key_Right:
                self._channel.send("\x1b[C")
            case Qt.Key.Key_Left:
                self._channel.send("\x1b[D")
            case Qt.Key.Key_Home:
                self._channel.send("\x1b[H")
            case Qt.Key.Key_End:
                self._channel.send("\x1b[F")
            case Qt.Key.Key_PageUp:
                self._channel.send("\x1b[5~")
            case Qt.Key.Key_PageDown:
                self._channel.send("\x1b[6~")
            case _:
                if text:
                    self._channel.send(text)


class TerminalWidget(QWidget):
    """Terminal SSH intégré avec contrôle de session."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channel: paramiko.Channel | None = None
        self._receiver: TerminalReceiver | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        top_bar = QHBoxLayout()
        self._status_label = QLabel("🖥️ Terminal SSH (Déconnecté)")
        self._status_label.setStyleSheet("font-weight: bold; color: #aaa;")
        top_bar.addWidget(self._status_label)

        top_bar.addStretch()

        self._clear_btn = QPushButton("Effacer")
        self._clear_btn.setFixedWidth(80)
        self._clear_btn.clicked.connect(self.clear_screen)
        top_bar.addWidget(self._clear_btn)

        layout.addLayout(top_bar)

        self._console = ConsoleEdit(self)
        layout.addWidget(self._console)

    def start_session(self, channel: paramiko.Channel):
        """Initialise le thread de réception et attache la console au canal SSH actif."""
        self.stop_session()
        self._channel = channel
        self._console.set_channel(channel)
        self._console.clear()

        self._receiver = TerminalReceiver(channel, self)
        self._receiver.data_received.connect(self._on_data_received)
        self._receiver.connection_lost.connect(self._on_connection_lost)
        self._receiver.start()

        self._status_label.setText("🖥️ Terminal SSH — Connecté")
        self._status_label.setStyleSheet("font-weight: bold; color: #2ecc71;")
        self._console.setFocus()

    def stop_session(self):
        """Interrompt la réception et libère le canal SSH associé."""
        if self._receiver:
            self._receiver.stop()
            self._receiver.wait(500)
            self._receiver = None

        if self._channel:
            try:
                self._channel.close()
            except Exception:
                pass
            self._channel = None

        self._console.set_channel(None)
        self._status_label.setText("🖥️ Terminal SSH (Déconnecté)")
        self._status_label.setStyleSheet("font-weight: bold; color: #aaa;")

    def _on_data_received(self, text: str):
        """Nettoie et insère le flux textuel reçu à la fin de la console."""
        # Élimine les séquences d'échappement ANSI pour éviter l'affichage de caractères de contrôle bruts
        clean_text = ANSI_ESCAPE_RE.sub("", text)
        clean_text = clean_text.replace("\r\n", "\n").replace("\r", "\n")

        cursor = self._console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(clean_text)
        self._console.setTextCursor(cursor)
        self._console.ensureCursorVisible()

    def _on_connection_lost(self):
        self._status_label.setText("🖥️ Terminal SSH (Session fermée)")
        self._status_label.setStyleSheet("font-weight: bold; color: #e74c3c;")

    def clear_screen(self):
        """Efface tout le contenu de la console."""
        self._console.clear()
