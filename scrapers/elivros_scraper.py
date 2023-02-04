import itertools
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
from yaspin import yaspin

from config.data_config import load_user_settings
from exceptions.exceptions import ScraperError
from models.uploader_models import ValidTopics, LibgenMetadata, AvailableSources
from history import HistoryHandler


class ELivrosDownloader:
    def __init__(self):

        self._base_url = r"https://elivros.love"
        self._rand_book_url = "http://elivros.love/page/RandomBook"
        self.history_service = HistoryHandler()
        self.first_run = True
        self.settings = load_user_settings()
        self.download_path = self.settings.downloads_path
        self.metadata: LibgenMetadata | None = None
        self.driver: WebDriver | None = None
        self.valid_extensions = ("epub", "pdf", "mobi")
        self.elapsed_time: int | None = None
        self.old_downloads: list[str] = []
        self.downloaded_filepaths: list[str] = []
        self.fiction_categories = [
            "Ficção",
            "Aventura",
            "Romance",
            "Contos",
            "Infanto",
            "Policial",
            "Humor",
            "Poemas",
            "Suspense",
        ]

    def _remove_invalid_file(self, file_path: str):
        try:
            os.remove(file_path)
        except (OSError, FileNotFoundError):
            logging.error(f"Could not remove file {file_path}")

    def _get_download_dir(self):
        return os.listdir(self.download_path)

    def _find_newly_added_files(self, old_downloads: list) -> list[str]:
        """
        Compares the difference between the older download list and the current one.
        Old list should be saved before making new downloads.
        Selenium offers no built-in way of retrieving this information.

        Only returns new entries, duplicates of main download folder are ignored.
        :param old_downloads:
        """

        downloads = self._get_download_dir()

        downloaded_filenames = []
        for filename in downloads:
            if filename not in old_downloads and filename.endswith(
                self.valid_extensions
            ):
                downloaded_filenames.append(filename)

        file_paths = [
            os.path.join(self.download_path, f_name) for f_name in downloaded_filenames
        ]

        return file_paths

    def _parse_html(self) -> BeautifulSoup:
        # Wait until page is loaded.
        info_element_locator = (By.CSS_SELECTOR, ".SerieAut")
        WebDriverWait(self.driver, 3).until(
            EC.visibility_of_element_located(info_element_locator)
        )
        soup = BeautifulSoup(self.driver.page_source, "lxml")

        return soup

    @staticmethod
    def _are_chrome_downloads_done(downloads_list: list[dict]):
        for download in downloads_list:
            d_state = download.get("state")
            if d_state == "IN_PROGRESS":
                return False

            return True

    def _monitor_chrome_downloads(self):
        """
        Checks if downloads are done.
        Chrome uses shadow root in the downloads list, so while possible i don't find it useful to implement
        a resume function. A lot of in-string JS would be necessary.

        The handle parameter determines the window in which to watch for chrome downloads.
        Get it using driver.window_handlers.

        """

        download_url = "chrome://downloads/"

        if self.driver.current_url != download_url:
            self.driver.get(download_url)

        # The only way to get elements from chrome's downloads list reasonably.
        downloads: list[dict] = self.driver.execute_script(
            """
        var items = document.querySelector('downloads-manager')
            .shadowRoot.getElementById('downloadsList').items;
        return items;
        
        """
        )

        if len(downloads) == 0:
            raise ScraperError("No downloads where started.")

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
                        f"Authors: {authors_series_info[1].get_text()}, Pages: {authors_series_info[2].get_text()}"
                    )
                    logging.error(f"Number of elements: {len(authors_series_info)}")
                    series_el = None
                else:
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
                logging.error(
                    f"Title is: {title_el.get_text()}, "
                    f"authors is: {authors_el.get_text()}, "
                    f"pages is: {pages_el.get_text()}, "
                    f"series is: {series_el}, "
                    f"and number of elements is {len(authors_series_info)}"
                )
                raise ScraperError(
                    "Invalid order for elements. Page element is not int. "
                    "Check logs for more info."
                )
        else:
            pages_text = None

        book_descr_el = soup.select_one("div.description > div.sinopse")

        try:
            metadata = LibgenMetadata(
                title=title_el.get_text(),
                authors=authors_el.get_text(),
                language="Portuguese",
                series=series_el,
                description=book_descr_el.get_text(),
                pages=pages_text,
                topic=topic,
                source=AvailableSources.elivros,
            )
        except ValidationError as e:
            logging.error(e, exc_info=True)
            raise ScraperError(e)

        return metadata

    def _get_random_page(self):
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "#metop > ul > li:nth-child(5) > a")
            )
        )

        random_el = self.driver.find_element(
            By.CSS_SELECTOR, "#metop > ul > li:nth-child(5) > a"
        )
        random_el.send_keys(Keys.RETURN)

    def navigate(self):
        # Takes the driver to the correct url for downloading.
        self.driver.get(self._rand_book_url)
        if self.first_run:
            self.driver.get(self._rand_book_url)

    def _start_downloading(self):
        WebDriverWait(self.driver, 3).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "#bookinfo > div.info > "
                    "div.downloads > "
                    "a.mainDirectLink.epub",
                )
            )
        )
        epub_el = self.driver.find_element(
            By.CSS_SELECTOR,
            "#bookinfo > div.info > div.downloads > a.mainDirectLink.epub",
        )

        pdf_el = self.driver.find_element(
            By.CSS_SELECTOR,
            "#bookinfo > div.info > div.downloads > a.mainDirectLink.pdf",
        )

        mobi_el = self.driver.find_element(
            By.CSS_SELECTOR,
            "#bookinfo > div.info > div.downloads > a.mainDirectLink.mobi",
        )

        for index, el in enumerate([epub_el, pdf_el, mobi_el]):
            try:
                el.send_keys(Keys.RETURN)
                time.sleep(4)

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
        self.old_downloads = self._get_download_dir()

        with yaspin(text=f"Downloading book") as spinner:

            spinner.write("Navigating to random")
            self.navigate()
            navigated_url = self.driver.current_url
            spinner.write(f"Downloading from {navigated_url}")
            spinner.write("Retrieving metadata")
            soup = self._parse_html()
            self.metadata = self.get_book_info(soup)

            spinner.write("Checking for duplicates")
            if self.history_service.check_duplicate(self.metadata):
                logging.warning(
                    f"URL '{navigated_url}' points to a metadata in queue or upload history. Skipping."
                )
                raise ScraperError(
                    "Current URL points to a metadata in queue or upload history. Skipping."
                )

            spinner.write("Starting download...")
            self._start_downloading()
            time.sleep(6)

            elapsed_time = 0
            seconds_per_iteration = 2
            done = False

            while not done:
                time.sleep(seconds_per_iteration)
                done = self._monitor_chrome_downloads()

                elapsed_time += seconds_per_iteration

            self.elapsed_time = elapsed_time

            self.downloaded_filepaths = self._find_newly_added_files(self.old_downloads)

            if len(self.downloaded_filepaths) == 0:
                logging.error(rf"Downloading failed for URL: {navigated_url}.")
                spinner.fail("Downloading failed. Check logs for more info.")
                raise ScraperError(rf"Downloading failed for URL: {navigated_url}.")

            spinner.write(
                f"Finished downloading {len(self.downloaded_filepaths)} files in {self.elapsed_time} seconds."
            )

            logging.info(
                f"Downloaded files '{self.downloaded_filepaths}' from {navigated_url} in "
                f"{self.elapsed_time} seconds."
            )
            logging.info(f"Files have been stored in {self.downloaded_filepaths}.")

            successful_attempts = 0
            for path in self.downloaded_filepaths:
                try:
                    self.history_service.add_to_history(self.metadata, path)
                    spinner.write(f"Added {path} to history.")
                    successful_attempts += 1
                except Exception as e:
                    logging.error(f"Failed to add {path} to history.")
                    logging.error(e, exc_info=True)
                    self._remove_invalid_file(path)
                    spinner.write(
                        f"Warning: Failed to add {path} to history. Check logs."
                    )

            if successful_attempts == 0:
                spinner.fail("❌")

            spinner.ok("✔")
