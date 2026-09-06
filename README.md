# FileDrop

Client SFTP graphique multiplateforme, moderne et sécurisé, développé en Python avec PyQt6 et Paramiko.

FileDrop propose une interface ergonomique à double panneau permettant d'explorer, transférer, synchroniser et éditer des fichiers sur des serveurs distants via les protocoles SSH et SFTP.

---

## Sommaire

- [Installation](#installation)
  - [Via les versions précompilées (Recommandé)](#via-les-versions-précompilées-recommandé)
  - [Depuis les sources (Python)](#depuis-les-sources-python)
- [Fonctionnalités](#fonctionnalités)
- [Sécurité et Authentification](#sécurité-et-authentification)
- [Exécution des Tests](#exécution-des-tests)
- [Compilation Autonome](#compilation-autonome)
- [Organisation du Projet](#organisation-du-projet)
- [Licence](#licence)

---

## Installation

### Via les versions précompilées (Recommandé)

Des binaires autonomes ne nécessitant aucune installation de Python sont compilés automatiquement pour chaque système d'exploitation.

Accédez directement à la page des téléchargements :
**[Télécharger la dernière version de FileDrop](https://github.com/VeloxxDev/FileDrop/releases/latest)**

| Système d'exploitation | Archive | Procédure d'installation |
| :--- | :--- | :--- |
| **Windows** | `FileDrop-Windows.zip` | Téléchargez l'archive, extrayez le dossier et lancez `FileDrop.exe`. |
| **Linux** | `FileDrop-Linux.tar.gz` | Extrayez l'archive (`tar -xvf FileDrop-Linux.tar.gz`) et exécutez le binaire `./FileDrop`. |
| **macOS** | `FileDrop-macOS.zip` | Téléchargez l'archive, extrayez-la et ouvrez l'application `FileDrop.app`. |

---

### Depuis les sources (Python)

#### Prérequis
- Python 3.10 ou version supérieure
- Gestionnaire de paquets `pip`
- Git

#### Procédure

1. Cloner le dépôt :
   ```bash
   git clone https://github.com/VeloxxDev/FileDrop.git
   cd FileDrop
   ```

2. Créer et activer un environnement virtuel (recommandé) :
   ```bash
   # Sous Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Sous Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Installer le paquet et ses dépendances :
   ```bash
   # Installation standard
   pip install .

   # Ou installation en mode développement (avec linters et outils de test)
   pip install -e ".[dev]"
   ```

4. Démarrer l'application :
   ```bash
   # Via la commande globale enregistrée
   filedrop

   # Ou directement via Python
   python main.py
   ```

---

## Fonctionnalités

### Double Explorateur de Fichiers
- **Panneaux synchronisés** : Panneau local à gauche (`QFileSystemModel`) et panneau distant SFTP à droite.
- **Fil d'Ariane interactif** : Navigation segment par segment avec saisie manuelle de chemin au clic.
- **Informations détaillées** : Tailles normalisées, dates de modification et permissions UNIX (`rwxr-xr-x`).
- **Affichage des éléments masqués** : Bascule immédiate des fichiers et dossiers cachés (dotfiles).
- **Glisser-Déposer (Drag and Drop)** : Transferts bidirectionnels entre panneaux et compatibilité avec le gestionnaire de fichiers de l'OS.

### File d'Attente et Gestion des Transferts
- **Exécution asynchrone non-bloquante** : Chaque transfert dispose de son propre worker thread (`QThread`) et canal SFTP dédié.
- **Limiteur de concurrence** : Gestion de pool configurable (3 transferts simultanés par défaut) pour prévenir la saturation des sessions serveur (`MaxSessions`).
- **Support des dossiers complets** : Transfert et téléchargement récursifs d'arborescences sans limite de profondeur.
- **Surveillance en temps réel** : Barres de progression, indicateur de vitesse de transfert et annulation unitaire.

### Édition Distante Directe
- Clic droit sur un fichier distant puis sélection de « Éditer ».
- Téléchargement sécurisé dans un espace temporaire et ouverture automatique dans l'éditeur système par défaut.
- Détection immédiate des sauvegardes (`QFileSystemWatcher`) et ré-expédition automatique vers le serveur distant.

### Terminal SSH Intégré
- Console interactive connectée directement au canal SSH via `invoke_shell()`.
- Nettoyage automatique des séquences d'échappement ANSI pour un affichage stable.
- Prise en charge des touches de navigation et des commandes usuelles.

### Ergonomie et Thèmes
- Thèmes Sombre et Clair intégrés avec bascule instantanée (`F10`).
- Raccourcis clavier standardisés (`F2` pour renommer, `Suppr` pour supprimer, `F5` pour actualiser, `Ctrl+,` pour les paramètres).

---

## Sécurité et Authentification

- **Méthodes d'authentification supportées** :
  - Authentification par mot de passe.
  - Clés privées SSH (`id_ed25519`, `id_rsa`, `.pem`) avec prise en charge des passphrases.
  - Agents SSH locaux (`ssh-agent`, Pageant).
- **Validation stricte des clés d'hôte** : Empreinte SHA-256 calculée et vérifiée interactivement lors de la première connexion pour empêcher les attaques de type Man-in-the-Middle (MitM).
- **Politique de confidentialité des données** : Les mots de passe ne sont jamais enregistrés sur le disque. Seuls les paramètres d'hôte, utilisateur et port sont mémorisés dans les favoris locaux.

---

## Exécution des Tests

Le projet intègre une suite de tests unitaires couvrant la logique réseau, les modèles, le formatage et les gestionnaires de configuration :

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Compilation Autonome

Pour recompiler manuellement l'application en binaire autonome pour votre plateforme actuelle :

```bash
pip install pyinstaller
python build.py
```

L'exécutable généré sera placé dans le répertoire `dist/FileDrop/`.

---

## Organisation du Projet

```text
FileDrop/
├── config/              Gestion des paramètres locaux et des favoris
├── core/                Moteur réseau Paramiko (SSH, SFTP, transferts, éditeur)
├── models/              Structures de données (dataclasses et énumérations)
├── ui/                  Composants graphiques PyQt6 et gestion des vues
├── utils/               Fonctions transversales (formatage, intégration OS)
├── resources/           Ressources statiques (icônes et feuilles de style QSS)
├── tests/               Suite de tests unitaires automatisés
├── .github/workflows/   Pipeline d'intégration et de compilation CI/CD
├── build.py             Script de compilation automatisée
├── filedrop.spec        Spécification multiplateforme PyInstaller
├── pyproject.toml        Configuration standard du package, dépendances et outils
├── requirements.txt     Liste des dépendances Python (rétrocompatibilité)
├── LICENSE              Licence open-source MIT
└── main.py              Point d'entrée de l'application
```

---

## Licence

Ce projet est distribué sous licence MIT.
