"""auteurs : Kadja Jean-Fabien Yoctan Yede ;  Cho Leslie Anabelle Yavo
description : programme qui permet d'ajouter, de supprimer et extraire des fichiers d'une archive"""

import sqlite3
import sys
import zlib
import os
from datetime import datetime
from os.path import curdir

from sqlar import *


def create_table(connection):
    """creation de la table sqlar."""
    with connection:
        connection.execute('''
               CREATE TABLE IF NOT EXISTS sqlar (
               name TEXT PRIMARY KEY,
               mode INTEGER,
               mtime INTEGER,
               sz INTEGER,
               data BLOB
               )
               ''')


def format_mtime(mtime):
    """fonction pour la conversion de mtime en date lisible"""
    return datetime.fromtimestamp(mtime).strftime("%a %b %d %H:%M:%S %Y")


def truncate_string(s, max_len):
    """Tronquer les noms de fichiers trop long."""
    if len(s) > max_len:
        return '...' + s[-(max_len - 3):]
    return s


def add_file_to_sqlar(connection, file, basename=None):
    """Ajoute un fichier à l'archive SQLAR."""
    if basename:
        nom = os.path.relpath(file, basename) # relpath permet obtenir le chemin relatif
    else:
        nom = os.path.basename(file)

    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlar WHERE name=?", (nom,))
    existing_file = cursor.fetchone()

    if existing_file:
        print(f"Le fichier '{nom}' existe déjà dans l'archive.")
        action = input("Souhaitez-vous l'écraser (e) ou l'ignorer (i) ? (e/i) : ").strip().lower()

        if action == "e":
            print(f"Fichier '{nom}' a été remplacé.")
            return

        if action == "i":
            print(f"Fichier '{nom}' ignoré.")
            return
        else:
            print("action non reconnue. le fichier sera ignoré")

    mode = os.stat(file).st_mode
    mtime = int(os.path.getmtime(file))
    sz = os.path.getsize(file)

    # Lecture et compression des données du fichier
    with open(file, 'rb') as f:
        data = f.read()
    compressed_data = zlib.compress(data)

    try:
        connection.execute(
            "INSERT OR REPLACE INTO sqlar (name, mode, mtime, sz, data) VALUES (?, ?, ?, ?, ?)",
            (nom, mode, mtime, sz, compressed_data)
        )
    except sqlite3.Error as e:
        print(f"Erreur SQLite lors de l'ajout : {e}")

def add_to_sqlar(connection, files):
    """Ajoute plusieurs fichiers ou dossiers à l'archive en appelant la focntion add_file_to_sqlar"""

    file_count = 0
    for file in files:
        if os.path.isfile(file):
            add_file_to_sqlar(connection, file)
            file_count += 1
        elif os.path.isdir(file):
            for root, _, filenames in os.walk(file):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    add_file_to_sqlar(connection, full_path, file)
                    file_count += 1
    print(f"{file_count} fichier(s) compressé(s) et ajouté(s) à SQLAR.")


def print_archives(rows):
    """Affiche les archives sous forme tabulaire."""
    header = ("Name", "Sz", "Last modified")
    tailles = [30, 9, 25]

    line_format = '| ' + ''.join([f"%-{v}s| " for v in tailles])
    horz_line = "-" * (len(line_format % header) - 1)

    print(horz_line)
    print(line_format % header)
    print(horz_line)

    for row in rows:
        last_modified = format_mtime(row[2])
        name = truncate_string(str(row[0]), tailles[0] - 1)
        data = (name, str(row[1]), last_modified)
        print(line_format % data)
    print(horz_line)


def list_sqlar(connection, element_par_page=10):
    """Liste les fichiers de l'archive """
    cursor = connection.cursor()
    cursor.execute("SELECT name, sz, mtime FROM sqlar")
    while True:
        rows = cursor.fetchmany(element_par_page)
        if not rows:
            print("Plus aucune donnée à afficher.")
            break
        print_archives(rows)
        choice = input("Appuyez sur Entrée pour continuer ou 'q' pour quitter> ")
        print()
        if choice.lower() == 'q':
            break
    cursor.close()


def extract_all_from_sqlar(connection, output_dir):
    """Extrait tous les fichiers de l'archive dans un répertoire."""
    cursor = connection.cursor()
    cursor.execute("SELECT name, mode, mtime, data FROM sqlar")

    for name, mode, mtime, compressed_data in cursor.fetchall():
        # Détermination du chemin complet du fichier à extraire
        file_path = os.path.join(output_dir, name)

        # Création des répertoires nécessaires pour le fichier, si non existants
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Décompression des données et écriture dans le fichier extrait
        with open(file_path, 'wb') as f:
            f.write(zlib.decompress(compressed_data))

        # Restauration des permissions du fichier et de la date de modification
        os.chmod(file_path, mode)
        os.utime(file_path, (mtime, mtime))

        print(f"Fichier extrait : {name} vers {file_path}")

    cursor.close()


def remove_from_sqlar(connection, file_name):
    """Supprime des fichiers de l'archive."""
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlar'")
    if cursor.fetchone() is None:
        print("Erreur : La table 'sqlar' n'existe pas dans l'archive.")
        return

    for name in file_name:
        cursor.execute("SELECT name From sqlar WHERE name =?", (name,))
        if cursor.fetchone() is None:
            print(f"Aucun fichier '{name}' n'est présent dans l'archive")
            continue # itérer dans chaque fichier passé en arguments

        with connection:
            connection.execute("DELETE FROM sqlar WHERE name=?", (name,))
            print(f"Fichier supprimé : {name}")

def __main__():

    if len(sys.argv) < 3:
        print("Usage : python sqlar.py archive.sqlar verb [options]")
        return

    # Récupération des arguments
    archive = sys.argv[1]
    verb = sys.argv[2]
    options = sys.argv[3:]

    # verification de l'existence de l'archive
    db_exist = os.path.exists(archive)

    connection = sqlite3.connect(archive)
    try:
        if verb == "add":
            if not db_exist:
                print(f"L'archive '{archive}' n'existe pas. Création en cours...")
                create_table(connection)
            if not options:
                print("Erreur : Aucun fichier ou répertoire spécifié pour 'add'")
                return
            add_to_sqlar(connection, options)

        elif verb == "remove":
            if not db_exist:
                print(f"Erreur : L'archive '{archive}' n'existe pas.")
                return
            if not options:
                print("Erreur : Aucun fichier ou répertoire spécifié pour 'remove'")
                return
            remove_from_sqlar(connection, options)

        elif verb == "list":
            if not db_exist:
                print(f"Erreur : L'archive '{archive}' n'existe pas.")
                return
            elements_par_page = 10
            if len(options) > 1:
                print("Usage de list : python sqlar.py archive.sqlar list [-p[number]] ")
                return
            if len(options) == 1:
                if not options[0].startswith("-p"):
                    print(f"Erreur : Option invalide '{options[0]}'. L'option doit commencer par '-p'.")
                    return
                else:
                    try:
                        elements_par_page = int(options[0].lstrip('-p'))
                    except ValueError:
                        print("Erreur : nombre invalide après '-p'")
                        return
            list_sqlar(connection, elements_par_page)

        elif verb == "extract":
            if not db_exist:
                print(f"Erreur : L'archive '{archive}' n'existe pas.")
                return
            if not options:
                print("Erreur : spécifiez un répertoire de sortie pour 'extract'")
                return
            extract_all_from_sqlar(connection, options[0])
        else:
            print(f"Commande inconnue : {verb}")
            print("Commandes disponibles : add, remove, list, extract")

    finally:
        connection.commit() # pour que la connexion reste ouverte pour enregistrer les modif
        connection.close()
        print("Connexion à la base de données fermée.")


if __name__ == "__main__":
    __main__()
