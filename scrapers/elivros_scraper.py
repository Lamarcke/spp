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

from config import setup_download_folder
from config.data_config import setup_temp_download_folder
from exceptions.exceptions import ScraperError
from models.history_models import DownloadHistoryEntry
from scrapers.helpers import ScraperHelper
from models.uploader_models import ValidTopics, LibgenMetadata, AvailableSources
from upload import HistoryHandler


class ELivrosDownloader:

    def __init__(self):

        self._base_url = r"https://elivros.love"
        self._rand_book_url = "http://elivros.love/page/RandomBook"
        self.history_service = HistoryHandler()
        self.first_run = True
        self.scraper_helper = ScraperHelper()
        self.temp_download_path = setup_temp_download_folder()
        self.download_path = setup_download_folder()
        self.metadata: LibgenMetadata | None = None
        self.driver: WebDriver | None = None
        self.valid_extensions = ("epub", "pdf", "mobi")
        self.elapsed_time: int | None = None
        self.old_downloads: list[str] = []
        self.downloaded_filepaths: list[str] = []
        self.fiction_categories = ["Ficção", "Aventura", "Romance",
                                   "Contos", "Infanto", "Policial", "Humor", "Poemas", "Suspense"]

    def _get_download_dir(self):
        return os.listdir(self.download_path)

    def _get_temp_download_dir(self):
        return os.listdir(self.temp_download_path)

    def _find_newly_added_files(self) -> list[str]:
        """
        Compares the difference between the older download list and the current one.
        Old list should be saved before making new downloads.
        Selenium offers no built-in way of retrieving this information.

        Only returns new entries, duplicates of main download folder are ignored.
        """

        temp_downloads = self._get_temp_download_dir()

        downloaded_filenames = []
        for filename in temp_downloads:
            if filename not in self.old_downloads and filename.endswith(self.valid_extensions):
                downloaded_filenames.append(filename)

        unique_filenames = self.scraper_helper.get_unique_filenames(downloaded_filenames)
        unique_filepaths = [os.path.join(self.temp_download_path, f_name) for f_name in unique_filenames]

        return unique_filepaths

    def _clean_temp_downloads(self):
        """
        Helper method that removes files in the temporary downloads folder.
        """

        for filename in self._get_temp_download_dir():
            path = os.path.join(self.temp_download_path, filename)
            try:
                os.remove(path)
            except OSError as e:
                logging.error(f"Error while cleaning temporary downloads. Error while removing file '{path}'")
                logging.error(f"{e}", exc_info=True)
                raise e

        logging.info("Cleaned temporary download folder.")

    def _parse_html(self) -> BeautifulSoup:
        # Wait until page is loaded.
        WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located((By.CSS_SELECTOR,
                                                                              ".SerieAut")))
        soup = BeautifulSoup(self.driver.page_source, "lxml")
        return soup

    def _are_downloads_done(self):
        """
        This is a file-based method to check if downloads are done.

        Prone to errors because chrome leaves failed downloads as .crdownload, which we are checking for.
        """
        dirlist = os.listdir(self.temp_download_path)
        downloading_extensions = (".tmp", ".crdownload")

        if len(dirlist) == 0:
            return False

        else:
            for filename in dirlist:
                if filename.endswith(downloading_extensions):
                    return False

        return True

    @staticmethod
    def _are_chrome_downloads_done(downloads_list: list[dict]):
        for download in downloads_list:
            d_state = download.get("state")
            if d_state == "IN_PROGRESS":
                return False

            return True

    def _prepare_download_monitor(self) -> tuple[str, str]:
        """
        This method opens a new tab that is going to be used by download_monitor().
        Should be called while the browser is in the main window.

        """

        main_page = self.driver.current_window_handle
        if len(self.driver.window_handles) == 2:
            downloads_page = self.driver.window_handles[1]

        else:
            self.driver.switch_to.new_window("tab")
            downloads_page = self.driver.current_window_handle
            self.driver.get(r"chrome://downloads/")
            self.driver.switch_to.window(main_page)

        return main_page, downloads_page

    def _monitor_chrome_downloads(self, handle: str):
        """
        Checks if downloads are done.
        Chrome uses shadow root in the downloads list, so while possible i don't find it useful to implement
        a resume function. A lot of in-string JS would be necessary.

        The handle parameter determines the window in which to watch for chrome downloads.
        Get it using driver.window_handlers.

        """

        download_url = "chrome://downloads/"

        if self.driver.current_window_handle != handle:
            self.driver.switch_to.window(handle)

        if self.driver.current_url != download_url:
            self.driver.get(download_url)

        # The only way to get elements from chrome's downloads list reasonably.
        downloads: list[dict] = self.driver.execute_script("""
        var items = document.querySelector('downloads-manager')
            .shadowRoot.getElementById('downloadsList').items;
        return items;
        
        """)

        return self._are_chrome_downloads_done(downloads)

    def get_book_info(self, soup: BeautifulSoup) -> LibgenMetadata:
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
                first_el_text = authors_series_info[0].get_text()
                if first_el_text.count("Vol:") == 0:
                    logging.error("Tried to add non-series value to series field.")
                    logging.error(f"Invalid value: {first_el_text}, other values:")
                    logging.error(
                        f"Authors: {authors_series_info[1].get_text()}, Pages: {authors_series_info[2].get_text()}")
                    logging.error(f"Number of elements: {len(authors_series_info)}")
                    raise ScraperError("Wrong value defined for Series, check logs.")
                series_el = authors_series_info[0]
                authors_el = authors_series_info[1]
                pages_el = authors_series_info[2]

        except (KeyError, AttributeError, ValueError) as e:
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
            except (TypeError, ValueError):
                logging.error("Tried to convert invalid element to page int.")
                logging.error("Elements are:")
                logging.error(f"Title is: {title_el.get_text()}, "
                              f"authors is: {authors_el.get_text()}, "
                              f"pages is: {pages_el.get_text()}, "
                              f"series is: {series_el}, "
                              f"and number of elements is {len(authors_series_info)}")
                raise ScraperError("Invalid order for elements. Page element is not int. "
                                   "Check logs for more info.")
        else:
            pages_text = None

        book_descr_el = soup.select_one("div.description > div.sinopse")

        try:
            metadata = LibgenMetadata(title=title_el.get_text(),
                                      authors=authors_el.get_text(),
                                      language="Portuguese",
                                      series=series_el,
                                      description=book_descr_el.get_text(),
                                      pages=pages_text,
                                      topic=topic,
                                      source=AvailableSources.elivros)
        except ValidationError as e:
            logging.error(e, exc_info=True)
            raise ScraperError(e)

        return metadata

    def _get_random_page(self):
        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "#metop > ul > li:nth-child(5) > a")))

        random_el = self.driver.find_element(By.CSS_SELECTOR, "#metop > ul > li:nth-child(5) > a")
        random_el.send_keys(Keys.RETURN)

    def navigate(self):
        # Takes the driver to the correct url for downloading.

        if self.driver.current_url not in [self._rand_book_url]:
            self.driver.get(self._rand_book_url)
            if self.first_run:
                self._get_random_page()

    def _start_downloading(self):
        WebDriverWait(
            self.driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#bookinfo > div.info > "
                                                                               "div.downloads > "
                                                                               "a.mainDirectLink.epub")))
        epub_el = self.driver.find_element(By.CSS_SELECTOR,
                                           "#bookinfo > div.info > div.downloads > a.mainDirectLink.epub")

        pdf_el = self.driver.find_element(By.CSS_SELECTOR,
                                          "#bookinfo > div.info > div.downloads > a.mainDirectLink.pdf")

        mobi_el = self.driver.find_element(By.CSS_SELECTOR,
                                           "#bookinfo > div.info > div.downloads > a.mainDirectLink.mobi")

        for index, el in enumerate([epub_el, pdf_el, mobi_el]):
            try:
                el.send_keys(Keys.RETURN)
                time.sleep(2)
            except:
                pass

    def get_metadata(self) -> LibgenMetadata:
        return self.metadata

    def make_download(self, driver: WebDriver):
        """
        Main method. Makes the actual downloading.

        Automatically builds and appends an entry to upload queue.

        Returns metadata relevant to the current file.

        throws ScraperError
        """

        self.driver = driver
        self._clean_temp_downloads()
        self.old_downloads = self._get_temp_download_dir()

        self.navigate()
        navigated_url = self.driver.current_url
        tab_handler = self._prepare_download_monitor()
        main_page = tab_handler[0]
        downloads_page = tab_handler[1]

        soup = self._parse_html()
        self.metadata = self.get_book_info(soup)
        self.first_run = False

        if self.history_service.exists_on_download_history(self.metadata):
            logging.warning(f"URL '{navigated_url}' points to a metadata in queue or upload history. Skipping.")
            raise ScraperError("Current URL points to a metadata in queue or upload history. Skipping.")

        self._start_downloading()

        elapsed_time = 0
        seconds_per_iteration = 1
        done = False

        while not done:
            time.sleep(seconds_per_iteration)
            done = self._monitor_chrome_downloads(downloads_page)
            elapsed_time += seconds_per_iteration

        self.driver.switch_to.window(main_page)
        self.elapsed_time = elapsed_time

        self.downloaded_filepaths = self._find_newly_added_files()

        if len(self.downloaded_filepaths) == 0:
            logging.error(fr"Downloading failed for URL: {navigated_url}. Files may be duplicates")
            raise ScraperError("Downloading failed for URL: {navigated_url}. Files may be duplicates")

        logging.info(f"Downloaded files '{self.downloaded_filepaths}' from {navigated_url} in "
                     f"{self.elapsed_time} seconds.")
        logging.info(f"Files have been temporarily stored in {self.downloaded_filepaths}.")

        history_entry = DownloadHistoryEntry(metadata=self.metadata, stored_at=self.downloaded_filepaths)
        self.history_service.add_to_download_history(history_entry)

        self._clean_temp_downloads()
