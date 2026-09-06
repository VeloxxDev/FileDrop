"""Exceptions personnalisées pour FileDrop."""


class FileDropError(Exception):
    """Classe de base pour toutes les erreurs FileDrop."""
    pass


class SSHConnectionError(FileDropError):
    """Erreur lors de la connexion SSH."""
    pass


class AuthenticationError(SSHConnectionError):
    """Échec de l'authentification (mot de passe incorrect, clé refusée)."""
    pass


class HostKeyError(SSHConnectionError):
    """Erreur de vérification de la clé du serveur."""
    def __init__(self, hostname: str, fingerprint: str):
        self.hostname = hostname
        self.fingerprint = fingerprint
        super().__init__(
            f"Clé inconnue pour {hostname} (fingerprint: {fingerprint})"
        )


class TransferError(FileDropError):
    """Erreur lors d'un transfert de fichier."""
    pass


class TransferCancelledError(TransferError):
    """Transfert annulé par l'utilisateur."""
    pass


class PermissionDeniedError(FileDropError):
    """Droits insuffisants sur un fichier ou dossier."""
    pass


class DisconnectedError(FileDropError):
    """La connexion SSH a été perdue."""
    pass
