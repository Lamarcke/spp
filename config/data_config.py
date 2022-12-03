import os
import sqlite3
from contextlib import contextmanager
from sqlite3 import Connection


def setup_temp_download_folder() -> str:
    temp_download_folder = os.environ.get("TEMP_DOWNLOAD_FOLDER")

    if not temp_download_folder:
        temp_download_folder = os.path.abspath(os.path.sep.join(("data", "temp")))

    temp_download_folder.encode(encoding="UTF-8")

    if not os.path.isdir(temp_download_folder):
        os.mkdir(temp_download_folder)

    return temp_download_folder


def setup_download_folder() -> str:
    download_folder = os.environ.get("DOWNLOAD_FOLDER")

    if not download_folder:
        download_folder = os.path.abspath(os.path.sep.join(("data", "downloads")))

    download_folder.encode(encoding="UTF-8")

    if not os.path.isdir(download_folder):
        os.mkdir(download_folder)
    return download_folder

def sqlite_conn():
    """
    Use this as a context manager.
    """
    db_path = os.path.sep.join(("data", "spp.db"))
    db_abs_path = os.path.abspath(db_path)
    conn = sqlite3.connect(db_abs_path)
    return conn

def setup_db():
    with sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS spp(id INTEGER PRIMARY KEY, 
                                                         metadata TEXT, 
                                                         filepath TEXT,
                                                         uploaded INTEGER DEFAULT 0,
                                                         uploaded_at TEXT DEFAULT NULL)""")

