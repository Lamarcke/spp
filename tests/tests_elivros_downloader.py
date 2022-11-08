from unittest import TestCase
import os


class TestElivrosDownloader(TestCase):

    def setUp(self) -> None:
        self.download_folder_path = os.path.abspath(r"example_temp_download")

    def test(self):
        print(self.download_folder_path)
