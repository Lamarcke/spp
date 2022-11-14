from fake_useragent import UserAgent
from selenium import webdriver
from dotenv import load_dotenv
import os

from selenium.webdriver.chrome.webdriver import WebDriver

from config.data_config import setup_temp_download_folder


def hosted_setup() -> WebDriver:
    ua = UserAgent()
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(f"user-agent={ua.random}")
    chrome_path = os.environ.get("CHROMEDRIVER_PATH")
    driver = webdriver.Chrome(executable_path=chrome_path, options=chrome_options)
    return driver


def local_setup() -> WebDriver:
    ua = UserAgent()
    download_folder = setup_temp_download_folder()
    options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_settings.popups": 0,
             "download.default_directory": download_folder,  # Set the path accordingly
             "download.prompt_for_download": False,  # change the downpath accordingly
             "download.directory_upgrade": True}
    # options.add_argument("--headless")
    options.add_argument(f"user-agent={ua.random}")
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver


def setup_driver() -> WebDriver:
    on_heroku = os.environ.get("ON_HEROKU")
    if on_heroku:
        driver = hosted_setup()
    else:
        driver = local_setup()

    return driver


load_dotenv()
