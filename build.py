"""Script de compilation automatique pour FileDrop avec PyInstaller."""

import os
import subprocess
import sys
from pathlib import Path


def build():
    """Lance la compilation de l'exécutable autonome via PyInstaller."""
    print("========================================")
    print("   Compilation de FileDrop (PyInstaller)")
    print("========================================")

    project_root = Path(__file__).resolve().parent
    spec_file = project_root / "filedrop.spec"

    if not spec_file.exists():
        print(f"Erreur : fichier {spec_file} introuvable.")
        sys.exit(1)

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_file)]

    print(f"Exécution : {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode == 0:
        dist_exe = project_root / "dist" / "FileDrop" / "FileDrop.exe"
        print("\n========================================")
        print("   Compilation réussie avec succès !")
        print(f"   Exécutable disponible dans :")
        print(f"   {dist_exe}")
        print("========================================")
    else:
        print(f"\nErreur lors de la compilation (code {result.returncode}).")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
