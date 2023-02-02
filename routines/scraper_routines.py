import logging
import os
import time

from selenium.common import WebDriverException

from config.driver_config import driver_setup
from history import HistoryHandler
from scrapers import ELivrosDownloader


def elivros_downloader(max_downloads_num: int = 0):
    """
    A pre-made script that runs the ELivrosDownloader with default configs and automatically handles errors.
    """
    scraper = ELivrosDownloader()
    history = HistoryHandler()
    driver = driver_setup()

    tries = 0

    while True:

        if max_downloads_num > 0:
            uploadable_entries = history.get_num_uploadable_entries()
            if uploadable_entries >= max_downloads_num:
                logging.info(f"Reached max downloads number ({max_downloads_num}).")
                print(f"Reached max downloads number ({max_downloads_num}).")
                break

        # Restart chrome driver every 20 attempts
        if tries > 0 and tries % 20 == 0:
            driver = driver_setup()
            scraper = ELivrosDownloader()
            history = HistoryHandler()
            tries = 0
            continue

        try:
            tries += 1
            scraper.make_download(driver)

        except WebDriverException as e:
            scraper = ELivrosDownloader()
            driver = driver_setup()
            continue

        except KeyboardInterrupt:
            break

        except BaseException as e:
            print(e)
