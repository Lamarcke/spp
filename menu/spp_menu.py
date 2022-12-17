import inquirer
import pyfiglet
from pydantic import BaseModel

from menu.spp_submenus import SPPScraperMenu


class SPPMenuOptions(BaseModel):
    # Do NOT call the start functions here!
    scraping = SPPScraperMenu().start
    settings = ""
    exit = ""

    class Config:
        arbitrary_types_allowed = True


class SPPMenu:
    def __init__(self):
        self.run = True
        self.menu_options = SPPMenuOptions()
        self.start_choices = [el for el in self.menu_options]

    def _show_figlet(self):
        figlet = pyfiglet.Figlet()
        print(figlet.renderText("SPP"))

    def _show_start_menu(self):
        while self.run:
            self._show_figlet()
            print("- Welcome to SPP -")
            print("- What will you be doing today? -")
            print("You can use CTRL + C to exit anytime.")

            menu = inquirer.list_input("Choose one option", choices=self.start_choices)
            menu()

    def start(self):
        self.run = True
        self._show_start_menu()

    def stop(self):
        # To be implemented.
        self.run = False
