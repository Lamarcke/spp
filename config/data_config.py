import json
import os
import sqlite3

from models.settings_models import SPPSettingsModel


def setup_data(user_settings: SPPSettingsModel):
    pass


def load_user_settings_file() -> SPPSettingsModel:
    default_settings = SPPSettingsModel()
    settings_path = os.path.abspath("spp_settings.json")
    if not os.path.isfile(settings_path):
        default_settings_json = default_settings.json()
        with open(settings_path) as f:
            f.write(default_settings_json)
        return default_settings

    with open(settings_path) as f:
        user_settings_json = json.load(f)
        user_settings = SPPSettingsModel(**user_settings_json)
        return user_settings
    
def load_user_settings():
    final_user_settings = load_user_settings_file()
    

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
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS spp(id INTEGER PRIMARY KEY,
                                                         metadata TEXT, 
                                                         filepath TEXT,
                                                         uploaded INTEGER DEFAULT 0,
                                                         uploaded_at TEXT DEFAULT NULL)"""
        )
