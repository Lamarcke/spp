import logging
import os
import time

from selenium import webdriver
from selenium.common import ElementNotSelectableException, WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from biblioterra_scraper.exceptions.exceptions import UploaderError
from biblioterra_scraper.models.uploader_models import LibgenMetadata, ValidTopics, UploadMetadataElements
from biblioterra_scraper.config import setup_upload_queue_log, setup_download_folder, setup_driver


class LibgenUpload:
    """
    This class uploads files from the download_folder to libgen, based on topic.
    You can use an active driver instance here.
    """

    def __init__(self, metadata: LibgenMetadata, driver: WebDriver = None):

        if driver is None:
            self.driver = setup_driver()
        else:
            self.driver = driver
        self.metadata = metadata
        self.username = "genesis"
        self.password = "upload"
        self.scitech_upload = f"https://{self.username}:{self.password}@library.bz/main/upload/"
        self.fiction_upload = f"https://{self.username}:{self.password}@library.bz/fiction/upload/"
        self.file_path: str | None = None
        self.download_path = setup_download_folder()
        self.upload_log = setup_upload_queue_log()

    @staticmethod
    def is_extension_valid(filename: str):
        valid_extensions = ["epub", "pdf"]
        for extension in valid_extensions:
            if filename.endswith(extension):
                return True

        return False

    @staticmethod
    def test_driver(driver: WebDriver):
        # Raises
        try:
            test = driver.current_url
            print(test)
        except WebDriverException as e:
            raise e

        except BaseException as e:
            raise WebDriverException("Driver is invalid.")

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
        return UploadMetadataElements(title=title_el, authors=authors_el,
                                      series=series_el, description=descr_el, pages=pages_el,
                                      language=language_el)

    def provide_metadata(self):
        fields = self._get_metadata_elements()

        fields.title.clear()
        fields.authors.clear()

        fields.title.send_keys(self.metadata.title)
        fields.authors.send_keys(self.metadata.authors)
        if self.metadata.series:
            fields.series.clear()
            fields.series.send_keys(self.metadata.series)
        if self.metadata.description:
            fields.description.clear()
            fields.description.send_keys(self.metadata.description)
        if self.metadata.pages:
            fields.pages.clear()
            fields.pages.send_keys(self.metadata.pages)
        if self.metadata.language:
            fields.language.clear()
            fields.language.send_keys(self.metadata.language)
        else:
            raise UploaderError("No language specified.")

    def finish_upload(self):
        submit_el = self.driver.find_element(By.CSS_SELECTOR, "#record_form > div > input")
        submit_el.click()
        uploaded_url_el = self.driver.find_element(By.CSS_SELECTOR, "body > div:nth-child(6) > a")
        uploaded_url = uploaded_url_el.get_attribute("href")
        return uploaded_url

    def _avoid_duplicates(self, filename: str):
        with open(self.upload_log, "r") as ul:
            for line in ul:
                if filename in line:
                    raise UploaderError("Duplicate upload.")

    def make_upload(self, filename: str):
        """
        Tries to upload "filename" to libgen.
        Note that filename should be a file name relative to the download_path.
        If no download path is set, will use the default one.
        e.g.:
        download_path = "C:\Download"
        filename = "a_book.epub"
        final path = "C:\a_book.epub"

        """

        self.file_path = rf"{self.download_path}\{filename}"
        self.navigate()
        try:
            self.send_file()
        except ElementNotSelectableException:
            raise UploaderError("Error while selecting file upload button. Libgen may be down.")
        self.provide_metadata()
        uploaded_url = self.finish_upload()
        logging.info(fr"Uploaded file '{file_path} to libgen, available at: '{uploaded_url}'")
        return uploaded_url
