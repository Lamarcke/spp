import logging
import os
import shutil

from selenium.common import (
    ElementNotSelectableException,
    NoSuchElementException,
    ElementNotVisibleException,
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from yaspin import yaspin

from exceptions import (
    HistoryError,
    HistoryFileError,
    UploaderHumanConfirmationError,
    UploaderDuplicateError,
    UploaderError,
    UploaderFileError,
)
from history import HistoryHandler
from models.uploader_models import (
    LibgenMetadata,
    ValidTopics,
    UploadMetadataElements,
    AvailableSources,
)


class LibgenUploadHandler:
    """
    This class uploads files from the download_folder to libgen, based on topic.
    You can use an active driver instance here.
    """

    def __init__(self):
        self.driver: WebDriver | None = None
        self.current_metadata: LibgenMetadata | None = None
        self.current_file_path: str | None = None
        self.username = "genesis"
        self.password = "upload"
        self.scitech_upload = (
            f"https://{self.username}:{self.password}@library.bz/main/upload/"
        )
        self.fiction_upload = (
            f"https://{self.username}:{self.password}@library.bz/fiction/upload/"
        )
        self.valid_extensions = ("epub", "pdf", "mobi")
        self.history_handler = HistoryHandler()

    def _handle_sending_errors(self, entry_id: int):
        """
        Handles errors that may happen after uploading a file, but before providing its metadata.
        """
        try:
            form_error: WebElement = self.driver.find_element(
                By.CSS_SELECTOR, "body > div.form_error"
            )
        except (
            NoSuchElementException,
            ElementNotVisibleException,
            ElementNotSelectableException,
        ):
            return

        form_error_text = form_error.text
        if form_error_text.find("already") != -1:
            logging.error(
                f"Libgen has deemed file as a duplicate on {self.current_metadata.topic} collection."
            )
            logging.error(f"File info: {self.current_file_path}")
            self.history_handler.mark_as_uploaded(entry_id)

        elif form_error_text.find("file size is below") != -1:
            logging.error("Libgen has deemed file as too small for upload.")
            logging.error(f"File info: {self.current_file_path}")
            logging.error("Removing from history while keeping the original file.")
            self.history_handler.remove_from_history(entry_id)

    def navigate(self):
        driver = self.driver

        if self.current_metadata.topic == "fiction":
            if self.driver.current_url != self.fiction_upload:
                driver.get(self.fiction_upload)

        else:
            if self.driver.current_url != self.scitech_upload:
                driver.get(self.scitech_upload)

    def _send_file(self):

        if self.current_file_path is None or not isinstance(
            self.current_file_path, str
        ):
            logging.error(
                "Trying to send invalid file. File is None or not a string filepath."
            )
            raise UploaderError("Trying to send invalid file.")

        file_btn = self.driver.find_element(
            By.CSS_SELECTOR,
            "body > div:nth-child(3) > form > input[type=file]:nth-child(1)",
        )
        file_btn.send_keys(self.current_file_path)

        upload_btn = self.driver.find_element(
            By.CSS_SELECTOR,
            "body > div:nth-child(3) > form > input[" "type=submit]:nth-child(2)",
        )
        upload_btn.click()

    def _get_metadata_elements(self):
        form_element_locator = (By.CSS_SELECTOR, "#record_form")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(form_element_locator)
        )

        if self.current_metadata.topic == ValidTopics.fiction:

            title_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(3) > li > label > input[type=text]",
            )
            authors_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(4) > li > label > input[type=text]",
            )
            series_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(5) > li:nth-child(3) > label > input[type=text]",
            )
            pages_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(5) > "
                "li:nth-child(4) > label > input[type=text]",
            )
            descr_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > div:nth-child(9) > label > "
                "textarea",
            )

            publisher_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > "
                "ul:nth-child(6) > li:nth-child(2) > label > "
                "input[type=text]",
            )

            language_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > "
                "ul:nth-child(5) > li:nth-child(1) > select",
            )
            language_el = Select(language_el)
        else:

            title_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(3) > "
                "li:nth-child(1) > label > input[type=text]",
            )
            authors_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(4) > li > label > input[type=text]",
            )
            series_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(5) > li:nth-child(3) > label > input[type=text]",
            )
            pages_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(5) > li:nth-child(4) > label > input[type=text]",
            )
            descr_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > div:nth-child(10) > label > textarea",
            )
            publisher_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(6) > li:nth-child(2) > label > input[type=text]",
            )
            language_el = self.driver.find_element(
                By.CSS_SELECTOR,
                "#record_form > fieldset:nth-child(2) > ul:nth-child(5) > li:nth-child(1) > select",
            )
            language_el = Select(language_el)

        return UploadMetadataElements(
            title=title_el,
            authors=authors_el,
            series=series_el,
            description=descr_el,
            pages=pages_el,
            language=language_el,
            publisher=publisher_el,
        )

    def _provide_metadata(self):
        fields = self._get_metadata_elements()

        fields.title.clear()
        fields.authors.clear()

        fields.title.send_keys(self.current_metadata.title)
        fields.authors.send_keys(self.current_metadata.authors)

        try:
            fields.language.select_by_visible_text(self.current_metadata.language)

        except:
            logging.error(
                f"Trying to upload file with invalid language value. {self.current_metadata.language}"
            )
            raise UploaderError(
                f"Trying to upload file with invalid language value. {self.current_metadata.language}"
            )

        sources_list = [source for source in AvailableSources]

        # Avoids problems with sources that set their own credits in files.
        fields.publisher.clear()

        if self.current_metadata.publisher:
            # If the source adds its own credits, add an empty string instead.
            if self.current_metadata.publisher in sources_list:
                self.current_metadata.publisher = ""

            fields.publisher.clear()
            fields.series.send_keys(self.current_metadata.publisher)

        if self.current_metadata.series:
            fields.series.clear()
            fields.series.send_keys(self.current_metadata.series)

        if self.current_metadata.description:
            fields.description.clear()
            fields.description.send_keys(self.current_metadata.description)

        if self.current_metadata.pages:
            fields.pages.clear()
            fields.pages.send_keys(self.current_metadata.pages)

    def _finish_upload(self):
        submit_el = self.driver.find_element(
            By.CSS_SELECTOR, "#record_form > div > input[type=submit]"
        )
        submit_el.click()

        try:
            uploaded_url_el = self.driver.find_element(
                By.CSS_SELECTOR, "body > div:nth-child(6) > a"
            )
            uploaded_url = uploaded_url_el.get_attribute("href")

        except BaseException as e:
            uploaded_url = None
            logging.error(f"Error while retrieving uploaded_url: {e}", exc_info=True)
            print(f"Error while retrieving uploaded_url: {e}")

        return uploaded_url

    def start_uploading(self, driver: WebDriver):
        """
        Main method.
        Upload to libgen the files available in the upload history.
        """

        self.driver = driver

        count_uploadable_entries = self.history_handler.get_num_uploadable_entries()
        if count_uploadable_entries == 0:
            logging.info("No uploadable entries in history.")
            print("No uploadable entries in history.")
            raise UploaderFileError("No uploadable entries in history.")

        for entry in self.history_handler.get_uploadable_history():

            if entry is None:
                continue

            with yaspin(text="Uploading file", color="yellow") as spinner:
                spinner.write(f"Uploading file: {entry.file_path}")
                self.current_metadata = entry.metadata
                self.current_file_path = entry.file_path
                spinner.write("Navigating to upload page")
                self.navigate()
                spinner.write("Sending file")
                try:
                    self._send_file()
                    spinner.write("Filling metadata form")
                    self._provide_metadata()
                except Exception:
                    # These errors generally happen before filling out metadata info.
                    self._handle_sending_errors(entry.entry_id)
                    spinner.write("Error while sending file. Check logs.")
                    spinner.fail("✘")
                    continue

                spinner.write("Finishing upload")
                upload_url = self._finish_upload()

                self.history_handler.mark_as_uploaded(entry.entry_id, upload_url)
                logging.info(f"Successfully uploaded file: {entry.file_path}")
                spinner.write("Marked as uploaded in history")
                spinner.ok("✔")
