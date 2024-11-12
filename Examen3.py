import sqlite3
import sys
import zlib
import os

from sqlar import *


def create_table(connection):
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


def truncate_string(s, max_len):
    if len(s) > max_len:
        return '...' + s[-(max_len - 3):]
    return s


def add_file_to_sqlar(connection, file, basename=None):
    # Nom et autres métadonnées du fichier
    if basename:
        if not len(file.split(basename + '\\')) == 0:
            nom = file.split(basename + '\\')[1]
        elif not len(file.split(basename + '/')) == 0:
            nom = file.split(basename + '/')[1]
    else:
        nom = os.path.basename(file)
    mode = os.stat(file).st_mode
    mtime = int(os.path.getmtime(file))
    sz = os.path.getsize(file)

    # Lecture et compression des données du fichier
    with open(file, 'rb') as f:
        data = f.read()
    compressed_data = zlib.compress(data)

    # Insertion dans la base SQLAR
    with connection:
        connection.execute(
            "INSERT INTO sqlar (name, mode, mtime, sz, data) VALUES (?, ?, ?, ?, ?)",
            (nom, mode, mtime, sz, compressed_data)
        )


def add_to_sqlar(connection, files):
    # args = sys.argv[2:]
    args = files.split(',')
    file_count = 0
    # Connexion à la base de données
    with connection:
        for arg in args:
            if os.path.isfile(arg):
                # Gérer les fichiers individuels
                add_file_to_sqlar(connection, arg)
                file_count += 1
            elif os.path.isdir(arg):
                base_name = os.path.basename(arg)
                # Gérer les répertoires et leurs fichiers
                for root, _, files in os.walk(arg):
                    for file in files:
                        full_path = os.path.join(root, file)
                        add_file_to_sqlar(connection, full_path, base_name)
                        file_count += 1
        print(f"{file_count} fichier(s) compressé(s) et ajouté(s) à SQLAR.")


def list_sqlar(connection):
    header = ("Name", "Sz", "Mtime")
    tailles = [30, len(header[2]) + 1, 20, ]
    line_format = '| ' + ''.join([f"%-{v}s| " for v in tailles])

    print(1)


def extract_all_from_sqlar(connection, output_dir):
    print(2)


def remove_from_sqlar(connection, file_name):
    for name in file_name:
        with connection:
            try:
                connection.execute('DELETE FROM sqlar WHERE name=?', (name,))
                print(f"Fichier supprimé : {name}")
            except sqlite3.Error as error:
                print(error)


def __main__():
    # Connexion à la base de données
    connection = sqlite3.connect('sqlar.db')
    try:
        # Création de la table si elle n'existe pas déjà
        create_table(connection)
        print("Table SQLAR créée ou déjà existante.")

        #     Phase de test
        #add_to_sqlar(connection, "C:\\Users\\202210233\\OneDrive - College D'Alma\\Documents\\Intranet\\TP4")
        remove_from_sqlar(connection, "Secondaire\\Test\\tp4secondaire_ip.txt")

    finally:
        # Fermeture de la connexion
        connection.close()
        print("Connexion à la base de données fermée.")


# Appel de la fonction principale
if __name__ == "__main__":
    __main__()
