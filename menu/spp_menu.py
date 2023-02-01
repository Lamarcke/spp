import os

import inquirer
import pyfiglet
from pydantic import BaseModel

from menu.spp_submenus import SPPScraperMenu, SPPUploadMenu
from routines.upload_routines import libgen_uploader

SPP_MENU_OPTIONS = {
    "scraping": SPPScraperMenu().start,
    "uploading": SPPUploadMenu().start,
    "settings": "",
    "exit": ""
}


class SPPMenu:
    def __init__(self):
        self.run = True
        self.menu_options = SPP_MENU_OPTIONS
        self.start_choices = [el for el in self.menu_options.keys()]

    def _show_figlet(self):
        figlet = pyfiglet.Figlet()
        print(figlet.renderText("SPP"))

    def _show_start_menu(self):
        while self.run:
            self._show_figlet()
            print("- Welcome to SPP -")
            print("- What will you be doing today? -")
            print("You can use CTRL + C to exit anytime.")

            choice = inquirer.list_input("Choose one option", choices=self.start_choices)
            self.menu_options[choice]()

    def start(self):
        self.run = True
        self._show_start_menu()

    def stop(self):
        # To be implemented.
        self.run = False
