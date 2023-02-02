import json
import os
import sqlite3

from models.settings_models import SPPSettingsModel


def _sqlite_conn():
    """
    Use this as a context manager.
    """
    user_settings = load_user_settings()
    db_path = user_settings.history_db_path
    conn = sqlite3.connect(db_path, timeout=60)

    return conn


def sqlite_conn_setup():
    conn = _sqlite_conn()
    with conn as conn_ctx:
        cursor = conn_ctx.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS spp(id INTEGER PRIMARY KEY,
                                                         metadata TEXT, 
                                                         filepath TEXT,
                                                         uploaded INTEGER DEFAULT 0,
                                                         uploaded_at TEXT DEFAULT NULL)"""
        )
    return conn


def _validate_user_settings(settings: SPPSettingsModel):
    download_path = settings.downloads_path
    temp_download_path = settings.temp_downloads_path
    if not os.path.isdir(download_path):
        os.mkdir(os.path.abspath(download_path))

    if not os.path.isdir(temp_download_path):
        os.mkdir(os.path.abspath(temp_download_path))


def load_user_settings() -> SPPSettingsModel:
    default_settings = SPPSettingsModel()
    settings_path = os.path.abspath("spp_settings.json")
    if not os.path.isfile(settings_path):
        default_settings_json = default_settings.json()
        with open(settings_path, "w+") as f:
            f.write(default_settings_json)

        if not os.path.isdir(os.path.abspath("data")):
            os.mkdir(os.path.abspath("data"))

        _validate_user_settings(default_settings)
        return default_settings

    with open(settings_path) as f:
        user_settings_json = json.load(f)
        user_settings = SPPSettingsModel(**user_settings_json)
        _validate_user_settings(user_settings)
        return user_settings
