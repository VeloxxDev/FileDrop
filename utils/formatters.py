"""Fonctions de formatage pour l'affichage (tailles, dates, permissions)."""

from datetime import datetime


def format_size(size_bytes: int) -> str:
    """Convertit un nombre d'octets en unité lisible (o, Ko, Mo, Go, To)."""
    if size_bytes < 0:
        return "?"
    if size_bytes == 0:
        return "0 o"

    units = ["o", "Ko", "Mo", "Go", "To"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def format_timestamp(timestamp: float | int) -> str:
    """Convertit un horodatage Unix en date formatée 'AAAA-MM-JJ HH:MM'."""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError):
        return "?"


def format_permissions(mode: int) -> str:
    """Convertit un mode Unix en chaîne de permissions 'rwxrwxrwx'."""
    perms = ""
    # Décalage par paquets de 3 bits pour les triplets propriétaire, groupe et autres
    for who in range(2, -1, -1):
        bits = (mode >> (who * 3)) & 0o7
        perms += "r" if bits & 4 else "-"
        perms += "w" if bits & 2 else "-"
        perms += "x" if bits & 1 else "-"
    return perms


def format_transfer_speed(bytes_per_second: float) -> str:
    """Formate un taux de transfert par seconde en chaîne lisible."""
    if bytes_per_second <= 0:
        return "0 o/s"
    return f"{format_size(int(bytes_per_second))}/s"
