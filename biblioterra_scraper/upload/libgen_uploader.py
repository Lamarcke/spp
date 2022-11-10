import logging
import os
import time
from copy import copy

from selenium import webdriver
from selenium.common import ElementNotSelectableException, WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from biblioterra_scraper.exceptions.exceptions import UploaderError
from biblioterra_scraper.models.uploader_models import LibgenMetadata, ValidTopics, UploadMetadataElements
from biblioterra_scraper.config import setup_upload_queue, setup_download_folder, setup_driver, setup_upload_history
from biblioterra_scraper.upload import UploadQueue


class LibgenUpload:
    """
    This class uploads files from the download_folder to libgen, based on topic.
    You can use an active driver instance here.
    """

    def __init__(self):
        self.driver: WebDriver | None = None
        self.metadata: LibgenMetadata | None = None
        self.username = "genesis"
        self.password = "upload"
        self.scitech_upload = f"https://{self.username}:{self.password}@library.bz/main/upload/"
        self.fiction_upload = f"https://{self.username}:{self.password}@library.bz/fiction/upload/"
        self.file_path: str | None = None
        self.queue = UploadQueue()
        self.download_path = setup_download_folder()
        self.upload_history = setup_upload_history()
        self.valid_extensions = ("epub", "pdf", "mobi")

    @staticmethod
    def _is_path_valid(file_path: str):
        file_path.encode("UTF-8")
        return os.path.isfile(file_path)

    def _is_extension_valid(self, file_path: str):
        if file_path.endswith(self.valid_extensions):
            return True

        return False

    def navigate(self):
        driver = self.driver
        if driver.current_url not in [self.fiction_upload, self.scitech_upload]:
            if self.metadata.topic == "fiction":
                driver.get(self.fiction_upload)

            else:
                driver.get(self.scitech_upload)

    def send_file(self):
        file_btn = self.driver.find_element(By.CSS_SELECTOR,
                                            "body > div:nth-child(3) > form > input[type=file]:nth-child(1)")
        file_btn.send_keys(self.file_path)

        upload_btn = self.driver.find_element(By.CSS_SELECTOR, "body > div:nth-child(3) > form > input["
                                                               "type=submit]:nth-child(2)")
        upload_btn.click()

    def _get_metadata_elements(self):
        if self.metadata.topic == ValidTopics.fiction:
            title_el = self.driver.find_element(By.CSS_SELECTOR,
                                                "#record_form > fieldset:nth-child(2) > ul:nth-child(3) > li "
                                                "> label > input[type=text]")
            authors_el = self.driver.find_element(By.CSS_SELECTOR,
                                                  "#record_form > fieldset:nth-child(2) > ul:nth-child(4) > "
                                                  "li > label > input[type=text]")
            series_el = self.driver.find_element(By.CSS_SELECTOR,
                                                 "#record_form > fieldset:nth-child(2) > ul:nth-child(5) > "
                                                 "li:nth-child(3) > label > input[type=text]")
            pages_el = self.driver.find_element(By.CSS_SELECTOR,
                                                "#record_form > fieldset:nth-child(2) > ul:nth-child(5) > "
                                                "li:nth-child(4) > label > input[type=text]")
            descr_el = self.driver.find_element(By.CSS_SELECTOR,
                                                "#record_form > fieldset:nth-child(2) > div:nth-child(9) > "
                                                "label > textarea")
            language_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                    "ul:nth-child(5) > li:nth-child(1) > input["
                                                                    "type=text]")
            language_el = Select(language_el)
        else:
            title_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                 "ul:nth-child(3) > li:nth-child(1) > label > input["
                                                                 "type=text]")
            authors_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                   "ul:nth-child(4) > li > label > input[type=text]")
            series_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                  "ul:nth-child(5) > li:nth-child(3) > label > input["
                                                                  "type=text]")
            pages_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                 "ul:nth-child(5) > li:nth-child(4) > label > input["
                                                                 "type=text]")
            descr_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                 "div:nth-child(10) > label > textarea")

            language_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                    "ul:nth-child(5) > li:nth-child(1) > input["
                                                                    "type=text]")
            language_el = Select(language_el)

        return UploadMetadataElements(title=title_el, authors=authors_el,
                                      series=series_el, description=descr_el, pages=pages_el,
                                      language=language_el)

    def provide_metadata(self):
        fields = self._get_metadata_elements()

        fields.title.clear()
        fields.authors.clear()

        fields.title.send_keys(self.metadata.title)
        fields.authors.send_keys(self.metadata.authors)
        try:
            fields.language.select_by_visible_text(self.metadata.language)

        except:
            logging.error(f"Trying to upload file with invalid language value. {self.metadata.language}")
            raise UploaderError(f"Trying to upload file with invalid language value. {self.metadata.language}")

        if self.metadata.series:
            fields.series.clear()
            fields.series.send_keys(self.metadata.series)
        if self.metadata.description:
            fields.description.clear()
            fields.description.send_keys(self.metadata.description)
        if self.metadata.pages:
            fields.pages.clear()
            fields.pages.send_keys(self.metadata.pages)

        else:
            raise UploaderError("No language specified.")

    def finish_upload(self):
        submit_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > div > input")
        submit_el.click()
        uploaded_url_el = self.driver.find_element(By.CSS_SELECTOR, "body > div:nth-child(6) > a")
        uploaded_url = uploaded_url_el.get_attribute("href")
        return uploaded_url

    def _is_entry_duplicated(self):
        """
        Check if the files of current metadata are duplicated.

        If they are, try to find unique ones.

        If there's none, entry is duplicated.
        :return: bool
        """

        # This script iterates through the current upload history, and removes duplicated files from the
        # current metadata object.
        # If the list of files is emptied, the metadata only has duplicated files,
        # and thus should not be uploaded.
        for entry in self.queue.get_current_history():
            if entry.metadata == self.metadata:
                unique_files = [file for file in self.metadata.filepaths
                                if file not in entry.metadata.filepaths]
                if len(unique_files) > 0:
                    self.metadata.filepaths = unique_files
                else:
                    return True

        return False

    def _check_and_fix_files(self):
        """
        Tests the current metadata object' files for invalid paths and extensions.
        """
        valid_files = []
        for file in self.metadata.filepaths:
            if self._is_path_valid(file) and self._is_extension_valid(file):

                valid_files.append(file)
            else:
                logging.warning(f"{file} is an invalid file. "
                                f"Files should be readable and point to an absolute path.")

        if len(valid_files) > 0:
            if len(valid_files) != len(self.metadata.filepaths):
                incorrect_files = [file for file in self.metadata.filepaths if file not in valid_files]
                logging.warning("Attempted to upload file with incorrect extensions or invalid paths.")
                logging.warning(f"Incorrect files: {incorrect_files}")
                logging.warning(f"Valid files: {valid_files}")

            self.metadata.filepaths = valid_files

        else:
            raise UploaderError("Provided metadata has invalid paths or extensions. "
                                "No file passed validation.")

    def make_upload(self, driver: WebDriver, metadata: LibgenMetadata):
        """
        Main method.
        Upload to libgen the files in the metadata object using it as source of information.
        """
        self.metadata = metadata
        self.driver = driver
        if self._is_entry_duplicated():
            raise UploaderError("Entry has already been uploaded. Skipping.")
        self._check_and_fix_files()
        self.navigate()
        # TODO





