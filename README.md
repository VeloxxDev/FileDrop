# 🚀 FileDrop — Client SFTP Graphique Moderne & Sécurisé

**FileDrop** est une application de bureau cross-platform (Windows, Linux, macOS) développée en **Python 3.10+** avec **PyQt6** et **Paramiko**, offrant une interface graphique fluide à double panneau pour gérer, transférer et éditer des fichiers via **SFTP/SSH**.

---

## ✨ Fonctionnalités Principales

### 📁 Navigation & Double Panneau
- **Double explorateur visuel :** Panneau local à gauche (`QFileSystemModel` natif) et panneau distant SFTP à droite.
- **Affichage complet :** Noms, tailles formatées (Ko, Mo, Go), dates de modification et permissions Unix (`rwxr-xr-x`).
- **Tri automatique :** Répertoires placés en tête, tri alphabétique insensible à la casse.
- **Toggle Fichiers Cachés :** Bouton œil (`👁`) dans chaque panneau pour afficher/masquer instantanément les dotfiles (`.bashrc`, `.git`, etc.).
- **Barres de chemin interactives :** Avec bouton remonter (`⬆`) et historique de navigation au double-clic.

### ⚡ Transferts & File d'Attente Intelligente (Pool Asynchrone)
- **Multi-threadé & Thread-safe :** Chaque transfert s'exécute dans un `QThread` avec son propre canal SFTP dédié (évite les conflits internes de Paramiko).
- **Limitation de concurrence :** Plafond intelligent à 3 transferts simultanés (configurable) pour ne jamais saturer le serveur SSH distant ni dépasser les quotas `MaxSessions`.
- **Transferts récursifs de dossiers :** Téléchargement et envoi d'arborescences complètes de dossiers sans limitation de profondeur.
- **Contrôle total :** Barres de progression individuelles (0-100%), bouton **Annuler** en temps réel et bouton **Nettoyer**.

### 🖱️ Glisser-Déposer (Drag & Drop) Avancé
- **Drag & Drop bidirectionnel :** Glissez des fichiers du panneau local vers le distant (Upload), ou du distant vers le local (Download).
- **Drag & Drop depuis l'OS :** Glissez directement des fichiers depuis l'Explorateur Windows vers le panneau distant FileDrop.
- **Aperçu visuel personnalisé :** Mini-aperçu "fantôme" élégant avec icône agrandie et bulle bleue Windows pour une lisibilité parfaite.
- **Dépôt ciblé :** Déposez un fichier directement sur un sous-dossier pour le ranger à l'intérieur.

### ✏️ Édition Distante Directe (Live Remote Editing)
- Clic droit sur un fichier distant -> **"✏️ Éditer le fichier"**.
- FileDrop télécharge le fichier dans un espace temporaire sécurisé et l'ouvre dans votre éditeur favori (VS Code, Notepad++, etc.).
- Dès que vous faites `Ctrl+S` dans votre éditeur, FileDrop détecte la modification via `QFileSystemWatcher` et ré-uploade automatiquement le fichier sur le serveur !

### 🖥️ Terminal SSH Interactif Intégré
- Console interactive intégrée dans l'onglet du bas.
- Exécutez directement vos commandes bash/sh sur le serveur (`ls`, `htop`, `git`, etc.).
- Prise en charge des raccourcis usuels (`Ctrl+C`, `Ctrl+D`, flèches de navigation, `Tab` pour l'autocomplétion).

### 🔒 Sécurité & Authentification
- **3 méthodes d'authentification :**
  1. Mot de passe
  2. Fichier de clé privée SSH (`id_ed25519`, `id_rsa`, `.pem` avec détection automatique et passphrase optionnelle)
  3. Agent SSH (`ssh-agent` sous Linux/macOS ou `Pageant` sous Windows)
- **Protection Anti-MitM :** Détection interactive et calcul d'empreinte SHA-256 des nouvelles clés d'hôte avec demande de validation utilisateur avant inscription dans `known_hosts`.
- **Gestionnaire de Favoris :** Mémorisation en un clic (`☆`) des couples hôte/identifiant avec menu déroulant sans stocker les mots de passe en clair.
- **Reconnexion automatique :** Surveillance de la liaison SSH toutes les 5 secondes et tentative de reconnexion automatique en cas de micro-coupure réseau.

### 🎨 Thèmes & Ergonomie
- **Thème Sombre & Thème Clair :** Feuilles de style QSS soignées, basculables à tout moment via le menu ou le raccourci `F10`.
- **Raccourcis Clavier :**
  - `F2` : Renommer l'élément sélectionné
  - `Suppr` : Supprimer (avec dialogue de confirmation)
  - `F5` : Rafraîchir le dossier actif
  - `Ctrl+,` : Préférences & Paramètres
  - `Ctrl+Q` : Quitter l'application

---

## 🛠️ Installation & Prérequis

### Prérequis
- Python 3.10 ou version supérieure
- Pip

### Installation des dépendances

```bash
git clone https://github.com/VeloxxDev/FileDrop.git
cd FileDrop
pip install -r requirements.txt
```

---

## 🚀 Démarrage

Pour lancer l'application en mode développement :

```bash
python main.py
```

---

## 🧪 Tests Unitaires

Une suite complète de tests unitaires avec mocks Paramiko et Qt est fournie :

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 📦 Compilation en Exécutable Autonome (.EXE Windows)

Pour générer un fichier exécutable indépendant ne nécessitant pas d'installation Python :

```bash
python build.py
```

L'exécutable compilé sera disponible dans :
`dist/FileDrop/FileDrop.exe`

---

## 🏗️ Structure du Projet

```text
FileDrop/
│
├── main.py                  # Point d'entrée de l'application
├── build.py                 # Script de build PyInstaller
├── filedrop.spec            # Configuration de packaging PyInstaller
├── requirements.txt         # Dépendances du projet
│
├── config/                  # Configuration & Persistance
│   ├── settings.py          # AppSettings (JSON)
│   └── favorites.py         # FavoritesManager (JSON)
│
├── core/                    # Moteur Métier & Réseau
│   ├── ssh_manager.py       # Connexion SSH, host key policy, keepalive
│   ├── sftp_manager.py      # Opérations SFTP, listing, stat
│   ├── transfer_worker.py   # QThread worker de transfert asynchrone
│   └── file_editor.py       # Surveillance et édition distante
│
├── models/                  # Modèles de Données (Dataclasses)
│   ├── connection_info.py   # Informations de connexion & auth
│   └── transfer_task.py     # Tâche de transfert et progression
│
├── ui/                      # Interface Graphique (PyQt6)
│   ├── main_window.py       # Fenêtre principale & orchestration
│   ├── connection_bar.py    # Barre supérieure & sélecteur de favoris
│   ├── local_panel.py       # Panneau explorateur local
│   ├── remote_panel.py      # Panneau explorateur distant SFTP
│   ├── transfer_queue.py    # File d'attente et progression visuelle
│   ├── terminal_widget.py   # Console terminal SSH interactive
│   ├── settings_dialog.py   # Dialogue des préférences utilisateur
│   ├── theme_manager.py     # Gestionnaire de thèmes QSS
│   └── ui_helpers.py        # Helpers partagés (D&D, raccourcis)
│
├── resources/               # Ressources graphiques
│   └── styles/              # Feuilles de style QSS
│       ├── dark.qss         # Thème sombre
│       └── light.qss        # Thème clair
│
├── tests/                   # Suite de tests automatisés
│   ├── test_ssh_manager.py
│   ├── test_sftp_manager.py
│   ├── test_transfer_worker.py
│   ├── test_favorites.py
│   └── test_formatters.py
│
└── utils/                   # Utilitaires système et formatage
    ├── exceptions.py        # Hiérarchie des exceptions personnalisées
    ├── formatters.py        # Formatage des tailles, dates et permissions
    └── platform_utils.py    # Chemins par défaut OS et clés SSH
```

---

## 📄 Licence

Ce projet est distribué sous licence MIT.
