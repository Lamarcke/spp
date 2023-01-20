import time

from selenium.common import WebDriverException

from config.driver_config import driver_setup
from scrapers import ELivrosDownloader


def elivros_downloader(tries: int = 0):
    """
    A pre-made script that runs the ELivrosDownloader with default configs and automatically handles errors.

    :param tries: number of tries to make (namely the number of books to download, but some may error out.)
    If set to 0, will run indefinitely.
    """
    scraper = ELivrosDownloader()
    driver = driver_setup()

    iterations = 0

    while True:
        if tries > 0:
            if iterations > tries:
                break

            iterations += 1

        scraper.make_download(driver)
        break
