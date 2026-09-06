"""Tests unitaires pour SSHManager."""

import unittest
from unittest.mock import MagicMock, patch

from core.ssh_manager import SSHManager
from models.connection_info import ConnectionInfo, AuthMethod
from utils.exceptions import AuthenticationError, HostKeyError, DisconnectedError


class TestSSHManager(unittest.TestCase):
    """Suite de tests pour le gestionnaire SSH."""

    def setUp(self):
        self.manager = SSHManager()
        self.conn_info = ConnectionInfo(
            host="srv.example.com",
            username="testuser",
            password="dummy_password",
            port=22,
            auth_method=AuthMethod.PASSWORD,
        )

    @patch("paramiko.SSHClient")
    def test_connect_password_success(self, mock_client_cls):
        """Vérifie la connexion réussie par mot de passe."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport

        self.manager.connect(self.conn_info)

        self.assertTrue(self.manager.is_connected)
        mock_client.connect.assert_called_once()
        kwargs = mock_client.connect.call_args[1]
        self.assertEqual(kwargs["hostname"], "srv.example.com")
        self.assertEqual(kwargs["username"], "testuser")
        self.assertEqual(kwargs["password"], "dummy_password")
        mock_transport.set_keepalive.assert_called_with(30)

    @patch("paramiko.SSHClient")
    def test_connect_authentication_failure(self, mock_client_cls):
        """Vérifie qu'une erreur d'authentification lève AuthenticationError."""
        import paramiko
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.connect.side_effect = paramiko.AuthenticationException("Auth error")

        with self.assertRaises(AuthenticationError):
            self.manager.connect(self.conn_info)

    def test_open_sftp_disconnected(self):
        """Vérifie que open_sftp lève DisconnectedError si non connecté."""
        with self.assertRaises(DisconnectedError):
            self.manager.open_sftp()

    def test_invoke_shell_disconnected(self):
        """Vérifie que invoke_shell lève DisconnectedError si non connecté."""
        with self.assertRaises(DisconnectedError):
            self.manager.invoke_shell()

    @patch("paramiko.SSHClient")
    def test_disconnect(self, mock_client_cls):
        """Vérifie la fermeture propre de la connexion."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport

        self.manager.connect(self.conn_info)
        self.manager.disconnect()

        self.assertFalse(self.manager.is_connected)
        mock_client.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
