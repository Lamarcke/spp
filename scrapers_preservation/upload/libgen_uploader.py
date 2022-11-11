import logging
import os
import shutil
import time
from copy import copy

from selenium import webdriver
from selenium.common import ElementNotSelectableException, WebDriverException, NoSuchElementException, \
    ElementNotVisibleException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

from scrapers_preservation.exceptions import UploadQueueError, UploadQueueFileError
from scrapers_preservation.exceptions.exceptions import UploaderError, UploaderFileError
from scrapers_preservation.models.uploader_models import LibgenMetadata, ValidTopics, UploadMetadataElements, \
    UploadedFileInfo
from scrapers_preservation.config import setup_upload_queue, setup_download_folder, setup_driver, setup_upload_history
from scrapers_preservation.upload import UploadQueue


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
        self.current_file_path: str | None = None
        self.upload_queue = UploadQueue()
        self.download_path = setup_download_folder()
        self.upload_history_path = setup_upload_history()
        self.temp_upload_history_path = os.path.abspath(r".\temp_upload_history.txt")
        self.valid_extensions = ("epub", "pdf", "mobi")

    @staticmethod
    def _is_path_valid(file_path: str):
        file_path.encode("UTF-8")
        return os.path.isfile(file_path)

    def _is_extension_valid(self, file_path: str):
        if file_path.endswith(self.valid_extensions):
            return True

        return False

    def _handle_sending_errors(self):
        """
        Handles errors that may happen after uploading a file, but before providing it's metadata.
        """
        try:
            form_error: WebElement = self.driver.find_element(By.CSS_SELECTOR, "body > div.form_error")
        except (NoSuchElementException, ElementNotVisibleException, ElementNotSelectableException):
            return

        form_error_text = form_error.text
        if form_error_text.find("already added") != -1:
            logging.error(f"Libgen has deemed file a duplicate on {self.metadata.topic} collection.")
            logging.error(f"File info: {self.current_file_path}")
            raise UploaderError(f"Libgen has deemed file {self.current_file_path} as a duplicate.")

    def navigate(self):
        driver = self.driver

        if self.metadata.topic == "fiction":
            if self.driver.current_url != self.fiction_upload:
                driver.get(self.fiction_upload)

        else:
            if self.driver.current_url != self.scitech_upload:
                driver.get(self.scitech_upload)

    def _send_file(self):

        if self.current_file_path is None or not isinstance(self.current_file_path, str):
            logging.error("Trying to send invalid file. File is None or not a string filepath.")
            raise UploaderError("Trying to send invalid file.")

        file_btn = self.driver.find_element(By.CSS_SELECTOR,
                                            "body > div:nth-child(3) > form > input[type=file]:nth-child(1)")
        file_btn.send_keys(self.current_file_path)

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

            publisher_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                     "ul:nth-child(5) > li:nth-child(1) > select")

            language_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                    "ul:nth-child(5) > li:nth-child(1) > select")
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

            publisher_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                     "ul:nth-child(6) > li:nth-child(2) > "
                                                                     "label > input[type=text]")

            language_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > fieldset:nth-child(2) > "
                                                                    "ul:nth-child(5) > li:nth-child(1) > select")
            language_el = Select(language_el)

        return UploadMetadataElements(title=title_el, authors=authors_el,
                                      series=series_el, description=descr_el, pages=pages_el,
                                      language=language_el, publisher=publisher_el)

    def _provide_metadata(self):
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

        if self.metadata.publisher:
            fields.publisher.clear()
            fields.series.send_keys(self.metadata.publisher)

        if self.metadata.series:
            fields.series.clear()
            fields.series.send_keys(self.metadata.series)

        if self.metadata.description:
            fields.description.clear()
            fields.description.send_keys(self.metadata.description)

        if self.metadata.pages:
            fields.pages.clear()
            fields.pages.send_keys(self.metadata.pages)

    def _finish_upload(self):
        submit_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > div > input[type=submit]")
        submit_el.click()

        try:
            uploaded_url_el = self.driver.find_element(By.CSS_SELECTOR, "body > div:nth-child(6) > a")
            uploaded_url = uploaded_url_el.get_attribute("href")

        except BaseException as e:
            uploaded_url = None
            logging.error(f"Error while retrieving uploaded_url: {e}", exc_info=True)
            print(f"Error while retrieving uploaded_url: {e}")

        return uploaded_url

    def _remove_duplicates(self):
        """
        Check if the files of current metadata are duplicated, if they are, remove the duplicates and tries
        to only use the unique ones

        If there's no unique file, throws UploaderError.
        :return: bool
        """

        # This script iterates through the current upload history, and removes duplicated files from the
        # current metadata object.
        # If the list of files is emptied, the metadata only has duplicated files,
        # and thus should not be uploaded.
        for history_entry in self.upload_queue.get_current_history():
            for file_path in self.metadata.filepaths:
                if file_path == history_entry.file_path:
                    self.metadata.filepaths.remove(file_path)

        if len(self.metadata.filepaths) == 0:
            logging.error("Trying to upload Metadata with no unique filepath.")
            logging.error(f"Metadata is: {self.metadata}")
            raise UploaderError("Metadata has no unique filepaths. Aborting upload.")

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
            raise UploaderError("Provided metadata file_paths only have invalid paths or extensions. "
                                "No file passed validation.")

    def add_to_history(self, upload_info: UploadedFileInfo):
        """
        Adds the uploaded file to the upload history.
        """

        upload_as_string = self.upload_queue.stringfy_uploaded_info(upload_info)
        with open(self.temp_upload_history_path, "w") as temp:
            for line in open(self.upload_history_path, "r"):
                temp.write(line)

            temp.write(f"{upload_as_string}\n")

        try:

            history_backup_file = os.path.abspath(r".\upload_history.backup")
            shutil.copy(self.upload_history_path, history_backup_file)
            shutil.move(self.temp_upload_history_path, self.upload_history_path)

            logging.info(f"Uploaded file {upload_info.file_path} to Libgen successfully.")
            logging.info(f"File is waiting moderation at {upload_info.available_at}")

        except (OSError, IOError) as e:
            logging.error("Error while saving upload info on upload history.")
            logging.error(f"{e}", exc_info=True)
            raise UploaderFileError(f"Error while saving upload info on upload history: {e}")

    def _make_file_upload(self, file_path: str):
        self.current_file_path = file_path
        self.navigate()
        self._send_file()
        self._handle_sending_errors()
        self._provide_metadata()
        time.sleep(60)
        upload_url = self._finish_upload()
        upload_info = UploadedFileInfo(file_path=self.current_file_path, available_at=upload_url)
        self.add_to_history(upload_info)

    def make_upload(self, driver: WebDriver, metadata: LibgenMetadata):
        """
        Main method.
        Upload to libgen the files in the metadata object using it as source of information.
        """
        self.metadata = metadata
        self.driver = driver

        self._remove_duplicates()
        self._check_and_fix_files()

        for filepath in self.metadata.filepaths:
            self._make_file_upload(filepath)

        try:
            self.upload_queue.remove_from_queue(metadata)
        except (UploadQueueError, UploadQueueFileError) as e:
            logging.error("A file that was uploaded couldn't be removed from upload queue.")
            logging.error(f"{e}", exc_info=True)
            raise e
