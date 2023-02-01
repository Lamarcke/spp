import os

import inquirer

from config.data_config import load_user_settings
from models.uploader_models import AvailableSources
from routines import elivros_downloader
from routines.upload_routines import libgen_uploader


class SPPScraperMenu:
    def __init__(self):
        self.settings = load_user_settings()
        self.max_downloads_num = self.settings.max_downloads

    def _handle_scraper_choice(self, choice: str):
        os.system("clear")

        if choice == AvailableSources.elivros:
            print(f"Starting {AvailableSources.elivros.value} scraper")
            print("You may close the scraper at any time by pressing CTRL + C"
                  "")
            elivros_downloader(self.max_downloads_num)

    def _show_scraper_menu(self):

        self.choices = [source.value for source in AvailableSources]

        while True:
            os.system("clear")
            print("Please choose the source which you want to scrap:")
            print("The scraper will download files and relevants metadata to the download folder.")
            print("If none is set, SPP will use the default /data/downloads folder.")
            choice = inquirer.list_input("Start scraping", choices=self.choices)

            self._handle_scraper_choice(choice)

    def start(self):
        self._show_scraper_menu()


class SPPUploadMenu:
    def __init__(self):
        pass

    def _show_upload_menu(self):
        while True:
            os.system("clear")
            libgen_uploader()

    def start(self):
        self._show_upload_menu()
