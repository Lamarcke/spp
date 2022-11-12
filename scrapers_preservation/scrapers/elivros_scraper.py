import logging
import os
import re
import shutil

from bs4 import BeautifulSoup
from pydantic import ValidationError

from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
import filecmp

from selenium.webdriver.support.wait import WebDriverWait

from scrapers_preservation.config import setup_download_folder
from scrapers_preservation.config.driver_config import setup_temp_download_folder
from scrapers_preservation.scrapers.base import Scraper
from scrapers_preservation.exceptions import UploadQueueError
from scrapers_preservation.exceptions.exceptions import ScraperError
from scrapers_preservation.scrapers.helpers import ScraperHelper
from scrapers_preservation.models.elivros_models import ElivrosMetadata
from scrapers_preservation.models.uploader_models import ValidTopics, LibgenMetadata, AvailableSources
from scrapers_preservation.upload import UploadQueue


class ELivrosDownloader(Scraper):

    def __init__(self):

        self.base_url = r"https://elivros.love"
        self._rand_book_url = "http://elivros.love/page/RandomBook"
        self.queue_service = UploadQueue()
        self.first_run = True
        self.book_info = None
        self.scraper_helper = ScraperHelper()
        self.temp_download_path = setup_temp_download_folder()
        self.download_path = setup_download_folder()
        self.metadata: ElivrosMetadata | None = None
        self.driver: WebDriver | None = None
        self.valid_extensions = ("epub", "pdf", "mobi")
        self.elapsed_time: int | None = None
        self.old_downloads: list[str] = []
        self.downloaded_filenames: list[str] = []
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
        """
        temp_downloads = self._get_temp_download_dir()

        downloaded_filenames = []
        for filename in temp_downloads:
            if filename not in self.old_downloads and filename.endswith(self.valid_extensions):
                downloaded_filenames.append(filename)

        return downloaded_filenames

    def _remove_files(self, files: list[str]):
        """
        Helper method that removes files in files parameter.

        :param files: a list of filenames
        """

        for filename in files:
            path = os.path.join(self.temp_download_path, filename)
            try:
                os.remove(path)
                self.downloaded_filenames.remove(filename)

            except (OSError, ValueError) as e:
                logging.error(f"Error while removing file '{path}'")
                logging.error(f"{e}", exc_info=True)
                raise e

    def _parse_html(self) -> BeautifulSoup:
        # Wait until page is loaded.
        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR,
                                                                               ".SerieAut")))
        soup = BeautifulSoup(self.driver.page_source, "lxml")
        return soup

    def _clean_temp_files(self):
        # Always call this before downloading new files.
        # Cleans everything that is not a valid format to avoid errors.

        valid_formats = self.valid_extensions

        temp_files = [file for file in self._get_temp_download_dir() if not file.endswith(valid_formats)]
        for file in temp_files:
            file_path = os.path.join(self.temp_download_path, file)
            try:
                os.remove(file_path)
            except (OSError, IOError) as e:
                print(f"File '{file_path} is being used by another process.'")
                raise e

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

        self.first_run = False

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

    def _move_valid_downloads(self):
        """
        Moves only valid files to the main download folder.

        Returns valid filenames. It may be an empty list if there's none.
        """

        moved_filepaths = []
        main_folder_filepaths = [os.path.join(self.download_path, filename) for filename in self._get_download_dir()]
        downloaded_filepaths = [os.path.join(self.temp_download_path, filename)
                                for filename in self.downloaded_filenames]

        # Very important!
        duplicates = self.scraper_helper.check_for_duplicate_files(downloaded_filepaths, main_folder_filepaths)

        for filename in self.downloaded_filenames:
            file_temp_path = os.path.join(self.temp_download_path, filename)
            file_main_path = os.path.join(self.download_path, filename)

            try:
                if file_temp_path not in duplicates:
                    shutil.move(file_temp_path, file_main_path)
                    moved_filepaths.append(file_main_path)
            except IOError as e:
                logging.error("Error while moving file: ")
                logging.error(f"File: {file_temp_path}")
                logging.error(e, exc_info=True)
                continue

        return moved_filepaths

    def get_scraper_metadata(self) -> ElivrosMetadata:
        return self.metadata

    def build_upload_entry(self, file_paths: list[str]) -> LibgenMetadata:
        if self.metadata is None:
            raise ScraperError("Metadata is None. Can't parse it to LibgenMetadata")

        try:
            # Elivros adds their own watermark on files, making libgen uploader detect these files as having
            # "elivros.love" as publisher. This is invalid and we want to avoid that.

            up_entry = LibgenMetadata(**self.metadata.dict(),
                                      filepaths=file_paths,
                                      source=AvailableSources.elivros,
                                      publisher="")

        except ValidationError as e:
            logging.error(f"Error while converting metadata '{self.metadata} to "
                          f"LibenMetadata. Scraping downloads. {e}", exc_info=True)

            raise ScraperError(
                f"Error while converting metadata '{self.metadata} to an UploadEntry. Scraping downloads'")

        return up_entry

    def append_to_queue(self, upload_entry: LibgenMetadata):

        try:
            self._remove_files(self._get_temp_download_dir())
            self._clean_temp_files()
            self.queue_service.add_to_queue(upload_entry)

        except UploadQueueError as e:
            self._remove_files(self._get_temp_download_dir())
            raise e

    def make_download(self, driver: WebDriver):
        """
        Main method. Makes the actual downloading.

        Automatically builds and appends an entry to upload queue.

        Returns metadata relevant to the current file.

        throws ScraperError
        """
        self.driver = driver
        self._clean_temp_files()
        self.old_downloads = self._get_temp_download_dir()

        self.navigate()
        tab_handler = self._prepare_download_monitor()
        main_page = tab_handler[0]
        downloads_page = tab_handler[1]

        soup = self._parse_html()
        self.metadata = self.get_book_info(soup)
        navigated_url = self.driver.current_url
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

        self.downloaded_filenames = self._find_newly_added_files()
        valid_file_paths = self._move_valid_downloads()

        if len(self.downloaded_filenames) == 0 or len(valid_file_paths) == 0:
            logging.error(fr"Downloading failed for URL: {navigated_url}")
            raise ScraperError("No new file has been downloaded")

        logging.info(f"Downloaded files '{self.downloaded_filenames}' from {navigated_url} in "
                     f"{self.elapsed_time} seconds.")
        logging.info(f"Files have been stored in {valid_file_paths}.")

        upload_entry = self.build_upload_entry(valid_file_paths)
        self.append_to_queue(upload_entry)
