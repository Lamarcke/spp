from fake_useragent import UserAgent
from selenium import webdriver
from dotenv import load_dotenv
import os

from selenium.webdriver.chrome.webdriver import WebDriver

from config.data_config import load_user_settings


def driver_setup(headless: bool = False) -> WebDriver:
    ua = UserAgent()
    user_settings = load_user_settings()

    download_folder = user_settings.downloads_path
    options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_settings.popups": 0,
             "download.default_directory": download_folder,  # Set the path accordingly
             "download.prompt_for_download": False,  # change the downpath accordingly
             "download.directory_upgrade": True}
    if headless:
        options.add_argument("--headless")
    options.add_argument(f"user-agent={ua.random}")
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver
