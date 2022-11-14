import time

from selenium.common import WebDriverException

from config import setup_driver
from scrapers import ELivrosDownloader
from exceptions import ScraperError


def elivros_downloader(tries: int = 0):
    """
    A pre-made script that runs the ELivrosDownloader with default configs and automatically handles errors.

    :param tries: number of tries to make (namely the number of books to download, but some may error out.)
    If set to 0, will run indefinitely.
    """
    scraper = ELivrosDownloader()
    driver = setup_driver()

    iterations = 0

    while True:
        if tries > 0:
            if iterations > tries:
                break

            iterations += 1

        try:
            scraper.make_download(driver)

        except WebDriverException as e:
            scraper = ELivrosDownloader()
            driver = setup_driver()
            print(e)
            continue

        except KeyboardInterrupt:
            break

        except BaseException as e:
            print(e)
