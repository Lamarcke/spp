import os

import inquirer

from models.uploader_models import AvailableSources
from routines import elivros_downloader


class SPPScraperMenu:

    def _handle_scraper_choice(self, choice: str):
        os.system("clear")

        if choice == AvailableSources.elivros:
            print(f"Starting {AvailableSources.elivros.value} scraper")
            print("You may close the scraper at any time by pressing CTRL + C"
                  "")
            elivros_downloader()

    def _show_scraper_menu(self):

        self.choices = [source.value for source in AvailableSources]

        while True:
            os.system("cls")
            print("Please choose the source which you want to scrap:")
            print("The scraper will download files and relevants metadata to the download folder.")
            print("If none is set, SPP will use the default /data/downloads folder.")
            choice = inquirer.list_input("Start scraping", choices=self.choices)

            self._handle_scraper_choice(choice)

    def start(self):
        self._show_scraper_menu()
