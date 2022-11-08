import logging
import os
import re

from bs4 import BeautifulSoup
from pydantic import ValidationError

from selenium.webdriver import Keys
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time

from selenium.webdriver.support.wait import WebDriverWait

from biblioterra_scraper.config import setup_download_folder
from biblioterra_scraper.download.base import Scraper
from biblioterra_scraper.exceptions import UploadQueueError
from biblioterra_scraper.exceptions.exceptions import ScraperError
from biblioterra_scraper.download.helpers import ScraperHelper
from biblioterra_scraper.models.elivros_models import ElivrosMetadata
from biblioterra_scraper.models.uploader_models import ValidTopics, LibgenMetadata, AvailableSources
from biblioterra_scraper.upload import UploadQueue
from biblioterra_scraper.upload.libgen_uploader import LibgenUpload


class ELivrosDownloader(Scraper):

    def __init__(self):
        self.base_url = r"https://elivros.love"
        self._rand_book_url = "http://elivros.love/page/RandomBook"
        self.queue_service = UploadQueue()
        self.helper = ScraperHelper()
        self.book_info = None
        self.download_path = setup_download_folder()
        self.metadata: ElivrosMetadata | None = None
        self.driver: WebDriver | None = None
        self.valid_extensions = ["epub", "pdf", "mobi"]
        self.old_downloads: list[str] = []
        self.downloaded_filenames: list[str] = []
        self.fiction_categories = ["Ficção", "Aventura", "Romance",
                                   "Contos", "Infanto", "Policial", "Humor", "Poemas", "Suspense"]

    def _get_download_dir(self):
        return os.listdir(self.download_path)

    def _find_newly_added_files(self) -> list[str]:
        """
        Compares the difference between the older download list and the current one.
        Old list should be saved before making new downloads.
        Selenium offers no built-in way of retrieving this information.
        """

        downloaded_filenames = []
        for filename in self._get_download_dir():
            if filename not in self.old_downloads:
                for extension in ["epub", "pdf"]:
                    if filename.endswith(extension):
                        downloaded_filenames.append(filename)

        return downloaded_filenames

    def _parse_html(self) -> BeautifulSoup:
        # Wait until page is loaded.
        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR,
                                                                               ".SerieAut")))
        soup = BeautifulSoup(self.driver.page_source, "lxml")
        return soup

    def _clean_temp_files(self):
        # Always call this before downloading new files.
        # Cleans everything that is not a valid format to avoid errors.
        valid_formats = (".epub", ".pdf")
        for filename in self._get_download_dir():
            if not filename.endswith(valid_formats):
                os.remove(filename)

    def _scrap_downloads(self):
        # Use this when something goes wrong and the recent downloaded files are not useful anymore.
        if len(self.downloaded_filenames) > 0:
            try:
                for filename in self.downloaded_filenames:
                    # For real string lol
                    file_path = fr"{self.download_path}\{filename}"
                    os.remove(file_path)
            except Exception as e:
                logging.error(f"Error while scraping invalid downloads: {e}")

    def _are_downloads_done(self):
        dirlist = os.listdir(self.download_path)
        downloading_extensions = (".tmp", ".crdownload")
        if len(dirlist) == 0:
            return False

        else:
            for filename in os.listdir(self.download_path):
                if filename.endswith(downloading_extensions):
                    return False

        return True

    def get_book_info(self, soup: BeautifulSoup) -> ElivrosMetadata:
        try:
            book_info_div = soup.select_one(".info")
            authors_series_info = book_info_div.select(".SerieAut > ul > li")
        except AttributeError as e:
            logging.error(e, exc_info=True)
            raise ScraperError(e)
        series_el = None
        authors_el = None
        pages_el = None
        try:
            if len(authors_series_info) == 1:
                authors_el = authors_series_info[0]
            elif len(authors_series_info) == 2:
                authors_el = authors_series_info[0]
                pages_el = authors_series_info[1]
            elif len(authors_series_info) > 2:
                series_el = authors_series_info[0]
                authors_el = authors_series_info[1]
                pages_el = authors_series_info[2]
        except (KeyError, AttributeError) as e:
            logging.error(e, exc_info=True)
            raise ScraperError(e)

        title_el = book_info_div.select_one("h1")
        topic_el = soup.select_one("#content > article > ul > li:nth-child(2) > a")
        topic_text = topic_el.get_text()

        # By default, a book is considered non-fiction.
        topic = ValidTopics.scitech

        # If the category is a part of any string inside self.fiction_categories, then it's fiction.
        for cat in self.fiction_categories:
            if topic_text.find(cat) != -1:
                topic = ValidTopics.fiction

        if series_el is not None:
            series_el = series_el.get_text()
        if pages_el is not None:
            pages_text = pages_el.get_text()
            pages_text = re.sub("Páginas", "", pages_text)
            try:
                pages_text = int(pages_text)
            except TypeError:
                pages_text = None
        else:
            pages_text = None

        book_descr_el = soup.select_one("div.description > div.sinopse")
        try:
            metadata = ElivrosMetadata(title=title_el.get_text(),
                                       authors=authors_el.get_text(),
                                       language="Portuguese",
                                       series=series_el,
                                       description=book_descr_el.get_text(),
                                       pages=pages_text,
                                       topic=topic)
        except ValidationError as e:
            logging.error(e, exc_info=True)
            raise ScraperError(e)

        return metadata

    @staticmethod
    def _get_random_page(driver: WebDriver):
        random_el = driver.find_element(By.CSS_SELECTOR, "#metop > ul > li:nth-child(5) > a")
        random_el.send_keys(Keys.RETURN)

    def navigate(self):
        # Takes the driver to the correct url for downloading.

        if self.driver.current_url not in [self._rand_book_url]:
            self.driver.get(self._rand_book_url)

        # self._get_random_page(self.driver)

    def _start_downloading(self):

        WebDriverWait(
            self.driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#bookinfo > div.info > "
                                                                               "div.downloads > "
                                                                               "a.mainDirectLink.epub")))
        epub = self.driver.find_element(By.CSS_SELECTOR, "#bookinfo > div.info > div.downloads > a.mainDirectLink.epub")

        pdf = self.driver.find_element(By.CSS_SELECTOR, "#bookinfo > div.info > div.downloads > a.mainDirectLink.pdf")

        mobi = self.driver.find_element(By.CSS_SELECTOR, "#bookinfo > div.info > div.downloads > a.mainDirectLink.pdf")

        epub.send_keys(Keys.LEFT_CONTROL + Keys.RETURN)
        pdf.send_keys(Keys.LEFT_CONTROL + Keys.RETURN)
        mobi.send_keys(Keys.LEFT_CONTROL + Keys.RETURN)

    def as_scraper_metadata(self) -> ElivrosMetadata:
        return self.metadata

    def as_libgen_metadata(self) -> LibgenMetadata:
        if self.metadata is None:
            raise ScraperError("Metadata is None. Can't parse it to LibgenMetadata")
        try:
            up_entry = LibgenMetadata(**self.metadata.dict(),
                                      filepaths=[fr"{self.download_path}\{filename}" for filename in
                                                 self.downloaded_filenames], source=AvailableSources.elivros)
        except ValidationError as e:
            self._scrap_downloads()

            logging.error(f"Error while converting metadata '{self.metadata} to "
                          f"LibenMetadata. Scraping downloads. {e}", exc_info=True)

            raise ScraperError(
                f"Error while converting metadata '{self.metadata} to an UploadEntry. Scraping downloads'")

        return up_entry

    def append_to_queue(self):
        upload_entry = self.as_libgen_metadata()
        try:
            self.queue_service.add_to_queue(upload_entry)
        except UploadQueueError as e:
            self._scrap_downloads()
            raise e

    def make_download(self, driver: WebDriver, timeout: int = 45) -> ElivrosMetadata:
        """
        Main method. Makes the actual downloading.

        Returns metadata relevant to the current file.

        Use class.get_downloaded_filenames after this to know which files where downloaded.
        Also logs the files in the default logging file.

        throws ScraperError
        """

        self.old_downloads = self._get_download_dir()

        self.driver = driver
        LibgenUpload.test_driver(self.driver)
        self._clean_temp_files()
        self.navigate()

        soup = self._parse_html()

        self.metadata = self.get_book_info(soup)
        self._start_downloading()

        seconds = 0
        while True:
            time.sleep(1)

            # Monitor downloads and resumes broken ones.
            self.helper.monitor_downloads(self.driver)

            if seconds > timeout:
                if self.metadata:
                    raise ScraperError(f"Failed to download {self.driver.current_url} due to timeout.")
                else:
                    raise ScraperError(f"Failed to download book due to timeout. Metadata couldn't be retrieved.")
            seconds += 1

            if self._are_downloads_done():
                break

        self.downloaded_filenames = self._find_newly_added_files()

        if len(self.downloaded_filenames) == 0:
            logging.error(fr"Downloading failed for URL: {self.driver.current_url}")
            raise ScraperError("No new file has been downloaded")

        self.append_to_queue()

        return self.metadata
