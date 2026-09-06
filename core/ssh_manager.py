"""Gestionnaire de connexion SSH via Paramiko.

Responsabilité : connexion, authentification, keepalive, reconnexion,
et politique interactive de vérification des clés d'hôte.
"""

import base64
import hashlib
import logging
from pathlib import Path

import paramiko

from models.connection_info import ConnectionInfo, AuthMethod
from utils.exceptions import (
    AuthenticationError,
    HostKeyError,
    DisconnectedError,
)

logger = logging.getLogger(__name__)


class InteractiveHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """Politique invitant l'utilisateur à valider toute clé d'hôte inconnue."""

    def __init__(self, callback, known_hosts_path: Path):
        self._callback = callback
        self._known_hosts_path = known_hosts_path

    def missing_host_key(self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey):
        sha256_fp = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode("ascii").rstrip("=")
        key_type = key.get_name()
        fingerprint_str = f"SHA256:{sha256_fp}"

        accepted = False
        if self._callback:
            try:
                accepted = self._callback(hostname, key_type, fingerprint_str)
            except Exception as e:
                logger.error("Erreur dans le callback host key : %s", e)
                accepted = False
        else:
            logger.warning("Aucun callback de vérification d'hôte défini pour %s", hostname)

        if not accepted:
            raise HostKeyError(hostname, fingerprint_str)

        client._host_keys.add(hostname, key_type, key)
        try:
            self._known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
            client.save_host_keys(str(self._known_hosts_path))
            logger.info("Nouvelle clé d'hôte acceptée et enregistrée pour %s", hostname)
        except Exception as e:
            logger.warning("Impossible d'enregistrer dans known_hosts : %s", e)


class SSHManager:
    """Gère la connexion SSH à un serveur distant."""

    def __init__(self):
        self._client: paramiko.SSHClient | None = None
        self._transport: paramiko.Transport | None = None
        self._connection_info: ConnectionInfo | None = None
        self._host_key_callback = None
        self._known_hosts_path = Path.home() / ".ssh" / "known_hosts"

    def set_host_key_callback(self, callback):
        """Enregistre la fonction de rappel appelée lors de la détection d'une clé d'hôte inconnue."""
        self._host_key_callback = callback

    @property
    def connection_info(self) -> ConnectionInfo | None:
        """Paramètres de la connexion actuellement active."""
        return self._connection_info

    def connect(
        self,
        connection_info: ConnectionInfo,
        timeout: int = 10,
        keepalive_interval: int = 30,
    ) -> None:
        """Établit et authentifie la session SSH selon les informations fournies."""
        self._connection_info = connection_info
        self._client = paramiko.SSHClient()

        if self._known_hosts_path.exists():
            try:
                self._client.load_host_keys(str(self._known_hosts_path))
            except Exception as e:
                logger.warning("Erreur chargement known_hosts : %s", e)

        self._client.set_missing_host_key_policy(
            InteractiveHostKeyPolicy(
                callback=self._host_key_callback,
                known_hosts_path=self._known_hosts_path,
            )
        )

        kwargs = {
            "hostname": connection_info.host,
            "port": connection_info.port,
            "username": connection_info.username,
            "timeout": timeout,
        }

        try:
            match connection_info.auth_method:
                case AuthMethod.PASSWORD:
                    kwargs["password"] = connection_info.password

                case AuthMethod.KEY_FILE:
                    kwargs["key_filename"] = connection_info.key_path
                    if connection_info.key_passphrase:
                        kwargs["passphrase"] = connection_info.key_passphrase
                    kwargs["look_for_keys"] = False
                    kwargs["allow_agent"] = False

                case AuthMethod.AGENT:
                    kwargs["allow_agent"] = True
                    kwargs["look_for_keys"] = False

            self._client.connect(**kwargs)

            self._transport = self._client.get_transport()
            # Maintient la connexion active pour éviter les déconnexions par les pare-feu/routeurs
            if self._transport and keepalive_interval > 0:
                self._transport.set_keepalive(keepalive_interval)

            logger.info("Connecté à %s", connection_info.display_name)

        except paramiko.AuthenticationException as e:
            raise AuthenticationError(
                f"Authentification échouée pour {connection_info.username}@"
                f"{connection_info.host}: {e}"
            ) from e
        except HostKeyError:
            raise
        except Exception as e:
            raise ConnectionError(
                f"Impossible de se connecter à {connection_info.host}:"
                f"{connection_info.port}: {e}"
            ) from e

    @property
    def is_connected(self) -> bool:
        """Indique si la liaison SSH sous-jacente est active."""
        if self._transport is None:
            return False
        return self._transport.is_active()

    @property
    def transport(self) -> paramiko.Transport | None:
        """Transport Paramiko actif pour l'ouverture de canaux auxiliaires."""
        return self._transport

    def open_sftp(self) -> paramiko.SFTPClient:
        """Ouvre un canal SFTP dédié et indépendant sur le transport actif."""
        if not self.is_connected:
            raise DisconnectedError("La connexion SSH n'est plus active.")
        return paramiko.SFTPClient.from_transport(self._transport)

    def invoke_shell(self) -> paramiko.Channel:
        """Ouvre un terminal interactif xterm-256color."""
        if not self.is_connected:
            raise DisconnectedError("La connexion SSH n'est plus active.")
        return self._client.invoke_shell(term="xterm-256color")

    def disconnect(self) -> None:
        """Ferme la session SSH et libère les ressources associées."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
            self._transport = None
            logger.info("Déconnecté.")

    def __del__(self):
        self.disconnect()
