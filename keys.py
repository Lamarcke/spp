from json import load

from dotenv import load_dotenv

from config.data_config import sqlite_conn_setup

sqlite_instance = sqlite_conn_setup()
