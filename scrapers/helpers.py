import filecmp
import itertools
import logging
import os
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.ie.webdriver import WebDriver

from config import setup_download_folder
from config.data_config import setup_temp_download_folder
from exceptions import ScraperError
from models.uploader_models import LibgenMetadata


class ScraperHelper:

    def __init__(self):
        self.downloads_path = setup_download_folder()

    def get_unique_filenames(self, filenames: list[str]):
        """
        A helper function that compares file names in 'filenames' against files in the main download folder.
        
        Should be used for finding duplicates in files.

        Always prefer this function over implementing a custom solution.
        
        'filenames' must be a list of filenames, not absolute paths.
        
        :returns a list of non-duplicates of 'compare'. may be empty.
        """

        duplicates = []

        for _, _, files in os.walk(self.downloads_path):
            for main_filename, compared_filename in zip(files, itertools.cycle(filenames)):
                if main_filename == compared_filename:
                    duplicates.append(compared_filename)

        valid_filenames = [f_name for f_name in filenames if f_name not in duplicates]
        return valid_filenames
