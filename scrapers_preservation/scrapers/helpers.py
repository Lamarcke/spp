import filecmp
import itertools
import logging
import os

from selenium.webdriver.common.by import By
from selenium.webdriver.ie.webdriver import WebDriver

from scrapers_preservation.config import setup_download_folder
from scrapers_preservation.config.driver_config import setup_temp_download_folder
from scrapers_preservation.exceptions import ScraperError


class ScraperHelper:

    def __init__(self):
        self.downloads_path = setup_download_folder()

    def _get_download_dir(self):
        return os.listdir(self.downloads_path)

    @staticmethod
    def check_for_duplicate_files(compare: list[str], against: list[str]):
        """
        A helper function that compares files in 'compare' against files in 'against'
        
        Should be used for finding duplicates in files.

        Always prefer this function over implementing a custom solution.
        
        Both 'compare' and 'against' must be lists of absolute paths.
        
        :returns a list of duplicates of 'compare'. may be empty.
        """
        
        # A little history of how this code has come to be:
        # A simple double for loop would make each entry compare against the whole dataset.
        # Meaning that, if we wanted to find a duplicate in a 5000-files folder, we would need to
        # compare every single file against 5000 files, 5000 times.
        # using zip() doesn't work because the files are not compared against every file in the folder.
        # Even itertools.combinations takes a really long time to iterate over everything.
        # So we needed to decrease the size of the dataset, and compare only against newly added files.

        duplicated_files = []

        for compared_path in compare:
            for against_path in against:
                # .cmp is set to perform shallow comparisons.
                if os.path.isfile(compared_path) and os.path.isfile(against_path):
                    if filecmp.cmp(compared_path, against_path):
                        duplicated_files.append(compared_path)
                else:
                    logging.error("Attempting comparison with invalid paths.")
                    logging.error(f"Check file permissions and existence: {compared_path, against_path}")
                    raise ScraperError("Attempting comparison with invalid paths. "
                                       f"Check file permissions and existence: {compared_path, against_path}")


        return duplicated_files
