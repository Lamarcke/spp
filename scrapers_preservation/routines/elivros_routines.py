import time

from selenium.common import WebDriverException

from scrapers_preservation.config import setup_driver
from scrapers_preservation.download import ELivrosDownloader
from scrapers_preservation.exceptions import ScraperError


def elivros_downloader():
    scraper = ELivrosDownloader()
    driver = setup_driver()

    while True:

        try:

            scraper.make_download(driver, 60)

        except WebDriverException as e:
            if e.msg == "Driver is invalid":
                driver = setup_driver()
            continue

        except KeyboardInterrupt:
            break

        except Exception as e:
            print(e)
            continue

        except BaseException as e:
            print(e)
            continue
