import inquirer
import pyfiglet

from menu.spp_submenus import SPPScraperMenu


class SPPMenu:
    def __init__(self):
        self.start_choices = ["scraping", "settings", "exit"]

    def _show_figlet(self):
        figlet = pyfiglet.Figlet()
        print(figlet.renderText("SPP"))

    def _show_start_menu(self):
        while True:
            self._show_figlet()
            print("- Welcome to SPP -")
            print("- What will you be doing today? -")
            print("You can use CTRL + C to exit anytime.")

            menu = inquirer.list_input("Choose one option", choices=self.start_choices)
            if menu == self.start_choices[0]:
                scraper_menu = SPPScraperMenu()
                scraper_menu.start()
            elif menu == self.start_choices[1]:
                pass
            elif menu == self.start_choices[2]:
                break

    def start(self):
        self._show_start_menu()


SPPMenu().start()
