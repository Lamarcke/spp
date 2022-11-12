from abc import ABCMeta, abstractmethod

from scrapers_preservation.models.uploader_models import LibgenMetadata


class Scraper(metaclass=ABCMeta):
    """
    Base class for all scrapers/downloaders.
    """

    @abstractmethod
    def append_to_queue(self, upload_entry: LibgenMetadata):
        pass

    @abstractmethod
    def _move_valid_downloads(self):
        """
        Moves valid downloads to download folder.
        """
        pass


