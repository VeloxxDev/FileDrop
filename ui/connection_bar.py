"""Barre de connexion SSH (zone supérieure de la fenêtre).

Permet de choisir entre 3 méthodes d'authentification :
- Mot de passe : saisie directe
- Clé SSH : sélection d'un fichier de clé privée (.pem, id_rsa, id_ed25519...)
- Agent SSH : utilise ssh-agent (Linux/macOS) ou Pageant (Windows)

Inclut un système de favoris avec menu déroulant et bouton étoile.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QComboBox,
    QFileDialog,
    QStackedWidget,
)
from PyQt6.QtCore import pyqtSignal, QTimer

from models.connection_info import ConnectionInfo, AuthMethod
from config.favorites import FavoritesManager
from utils.platform_utils import get_default_ssh_key_paths


class ConnectionBar(QWidget):
    """Barre de connexion avec favoris, champs host/user/auth, port.

    Signals:
        connect_requested(ConnectionInfo): Émis quand l'utilisateur clique sur Connexion.
        disconnect_requested(): Émis quand l'utilisateur clique sur Déconnexion.
    """

    connect_requested = pyqtSignal(ConnectionInfo)
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_connected = False
        self._favorites_manager = FavoritesManager()
        self._setup_ui()
        self._refresh_favorites_combo()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        row1 = QHBoxLayout()

        row1.addWidget(QLabel("Favoris :"))
        self._favorites_combo = QComboBox()
        self._favorites_combo.setMinimumWidth(200)
        self._favorites_combo.setPlaceholderText("Saisie manuelle")
        self._favorites_combo.currentIndexChanged.connect(self._on_favorite_selected)
        row1.addWidget(self._favorites_combo)

        self._save_fav_button = QPushButton("☆")
        self._save_fav_button.setToolTip("Ajouter aux favoris")
        self._save_fav_button.setFixedWidth(30)
        self._save_fav_button.setStyleSheet(
            "QPushButton { font-size: 16px; }"
            "QPushButton:hover { color: #f1c40f; }"
        )
        self._save_fav_button.clicked.connect(self._on_save_favorite)
        row1.addWidget(self._save_fav_button)

        self._del_fav_button = QPushButton("✕")
        self._del_fav_button.setToolTip("Supprimer ce favori")
        self._del_fav_button.setFixedWidth(30)
        self._del_fav_button.setStyleSheet(
            "QPushButton { font-size: 12px; color: #888; }"
            "QPushButton:hover { color: #e74c3c; }"
        )
        self._del_fav_button.clicked.connect(self._on_delete_favorite)
        row1.addWidget(self._del_fav_button)

        separator = QLabel("│")
        separator.setStyleSheet("color: #555;")
        row1.addWidget(separator)

        row1.addWidget(QLabel("Hôte :"))
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("serveur.exemple.fr")
        self._host_input.setMinimumWidth(160)
        row1.addWidget(self._host_input)

        row1.addWidget(QLabel("Identifiant :"))
        self._user_input = QLineEdit()
        self._user_input.setPlaceholderText("nom_utilisateur")
        self._user_input.setMinimumWidth(100)
        row1.addWidget(self._user_input)

        row1.addWidget(QLabel("Port :"))
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(22)
        self._port_input.setFixedWidth(70)
        row1.addWidget(self._port_input)

        self._connect_button = QPushButton("Connexion")
        self._connect_button.setFixedWidth(130)
        self._connect_button.clicked.connect(self._on_button_clicked)
        row1.addWidget(self._connect_button)

        main_layout.addLayout(row1)

        row2 = QHBoxLayout()

        row2.addWidget(QLabel("Authentification :"))
        self._auth_combo = QComboBox()
        self._auth_combo.addItem("Mot de passe", AuthMethod.PASSWORD)
        self._auth_combo.addItem("Clé SSH", AuthMethod.KEY_FILE)
        self._auth_combo.addItem("Agent SSH", AuthMethod.AGENT)
        self._auth_combo.setFixedWidth(140)
        self._auth_combo.currentIndexChanged.connect(self._on_auth_method_changed)
        row2.addWidget(self._auth_combo)

        self._auth_stack = QStackedWidget()

        password_page = QWidget()
        pw_layout = QHBoxLayout(password_page)
        pw_layout.setContentsMargins(0, 0, 0, 0)
        pw_layout.addWidget(QLabel("Mot de passe :"))
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setMinimumWidth(150)
        self._password_input.returnPressed.connect(self._on_button_clicked)
        pw_layout.addWidget(self._password_input)
        self._auth_stack.addWidget(password_page)

        key_page = QWidget()
        key_layout = QHBoxLayout(key_page)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(QLabel("Clé privée :"))
        self._key_path_input = QLineEdit()
        self._key_path_input.setPlaceholderText("~/.ssh/id_ed25519")
        self._key_path_input.setMinimumWidth(200)
        existing_keys = get_default_ssh_key_paths()
        if existing_keys:
            self._key_path_input.setText(str(existing_keys[0]))
        key_layout.addWidget(self._key_path_input)
        self._key_browse_button = QPushButton("Parcourir...")
        self._key_browse_button.setFixedWidth(100)
        self._key_browse_button.clicked.connect(self._browse_key_file)
        key_layout.addWidget(self._key_browse_button)
        key_layout.addWidget(QLabel("Passphrase :"))
        self._passphrase_input = QLineEdit()
        self._passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._passphrase_input.setPlaceholderText("(vide si non protégée)")
        self._passphrase_input.setMinimumWidth(120)
        self._passphrase_input.returnPressed.connect(self._on_button_clicked)
        key_layout.addWidget(self._passphrase_input)
        self._auth_stack.addWidget(key_page)

        agent_page = QWidget()
        agent_layout = QHBoxLayout(agent_page)
        agent_layout.setContentsMargins(0, 0, 0, 0)
        self._agent_label = QLabel(
            "L'agent SSH (ssh-agent / Pageant) sera utilisé automatiquement."
        )
        self._agent_label.setStyleSheet("color: #888; font-style: italic;")
        agent_layout.addWidget(self._agent_label)
        agent_layout.addStretch()
        self._auth_stack.addWidget(agent_page)

        row2.addWidget(self._auth_stack, stretch=1)
        main_layout.addLayout(row2)

    def _refresh_favorites_combo(self):
        """Recharge la liste déroulante des favoris enregistrés."""
        self._favorites_combo.blockSignals(True)
        self._favorites_combo.clear()

        self._favorites_combo.addItem("— Saisie manuelle —", None)

        for fav in self._favorites_manager.favorites:
            self._favorites_combo.addItem(fav.display_name, fav)

        self._favorites_combo.setCurrentIndex(0)
        self._favorites_combo.blockSignals(False)

    def _on_favorite_selected(self, index: int):
        """Injecte les identifiants du favori sélectionné dans le formulaire."""
        if index <= 0:
            self._host_input.clear()
            self._user_input.clear()
            self._port_input.setValue(22)
            self._password_input.clear()
            self._key_path_input.clear()
            self._passphrase_input.clear()
            self._auth_combo.setCurrentIndex(0)
            return

        fav: ConnectionInfo | None = self._favorites_combo.currentData()
        if fav is None:
            return

        self._fill_from_connection_info(fav)

    def _on_save_favorite(self):
        """Enregistre la configuration courante dans le gestionnaire de favoris."""
        host = self._host_input.text().strip()
        user = self._user_input.text().strip()

        if not host or not user:
            return

        auth_method: AuthMethod = self._auth_combo.currentData()
        info = ConnectionInfo(
            host=host,
            username=user,
            port=self._port_input.value(),
            auth_method=auth_method,
        )

        if auth_method == AuthMethod.KEY_FILE:
            info.key_path = self._key_path_input.text().strip()

        self._favorites_manager.add(info)
        self._refresh_favorites_combo()
        self._favorites_combo.setCurrentIndex(1)

        # Indique temporairement à l'utilisateur la confirmation de la sauvegarde
        self._save_fav_button.setText("★")
        QTimer.singleShot(1500, lambda: self._save_fav_button.setText("☆"))

    def _on_delete_favorite(self):
        """Retire le favori actif de la configuration persistée."""
        index = self._favorites_combo.currentIndex()
        if index <= 0:
            return

        # Décalage d'un cran en raison de l'option initiale 'Saisie manuelle'
        fav_index = index - 1
        self._favorites_manager.remove(fav_index)
        self._refresh_favorites_combo()

    def _on_auth_method_changed(self, index: int):
        """Affiche les champs correspondant au mode d'authentification sélectionné."""
        self._auth_stack.setCurrentIndex(index)

    def _browse_key_file(self):
        """Ouvre l'explorateur pour choisir un fichier de clé privée."""
        ssh_dir = str(Path.home() / ".ssh")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner une clé SSH privée",
            ssh_dir,
            "Tous les fichiers (*)",
        )
        if path:
            self._key_path_input.setText(path)

    def _on_button_clicked(self):
        """Déclenche la demande de connexion ou déconnexion selon l'état actuel."""
        if self._is_connected:
            self.disconnect_requested.emit()
            return

        auth_method: AuthMethod = self._auth_combo.currentData()

        connection_info = ConnectionInfo(
            host=self._host_input.text().strip(),
            username=self._user_input.text().strip(),
            port=self._port_input.value(),
            auth_method=auth_method,
        )

        match auth_method:
            case AuthMethod.PASSWORD:
                connection_info.password = self._password_input.text()
            case AuthMethod.KEY_FILE:
                connection_info.key_path = self._key_path_input.text().strip()
                passphrase = self._passphrase_input.text()
                connection_info.key_passphrase = passphrase if passphrase else None
            case AuthMethod.AGENT:
                pass

        self.connect_requested.emit(connection_info)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def set_connected(self, connected: bool):
        """Adapte l'intitulé du bouton et l'accessibilité des champs à l'état de la connexion."""
        self._is_connected = connected
        self._connect_button.setText(
            "Déconnexion" if connected else "Connexion"
        )
        # Verrouille les champs pendant qu'une session est active pour éviter les modifications accidentelles
        for widget in (
            self._host_input,
            self._user_input,
            self._port_input,
            self._auth_combo,
            self._password_input,
            self._key_path_input,
            self._key_browse_button,
            self._passphrase_input,
            self._favorites_combo,
            self._save_fav_button,
            self._del_fav_button,
        ):
            widget.setEnabled(not connected)

    def _fill_from_connection_info(self, info: ConnectionInfo):
        """Injecte les informations de connexion dans les champs correspondants."""
        self._host_input.setText(info.host)
        self._user_input.setText(info.username)
        self._port_input.setValue(info.port)

        for i in range(self._auth_combo.count()):
            if self._auth_combo.itemData(i) == info.auth_method:
                self._auth_combo.setCurrentIndex(i)
                break

        if info.key_path:
            self._key_path_input.setText(info.key_path)
