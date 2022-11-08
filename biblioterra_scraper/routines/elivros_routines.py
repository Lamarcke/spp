from biblioterra_scraper.config import setup_driver
from biblioterra_scraper.download import ELivrosDownloader
from biblioterra_scraper.exceptions import ScraperError


def elivros_downloader():
    scraper = ELivrosDownloader()
    driver = setup_driver()
    while True:
        try:
            scraper.make_download(driver, 60)
        except Exception as e:
            print(e)
            continue

        except BaseException as e:
            break




