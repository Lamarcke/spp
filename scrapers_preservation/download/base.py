from abc import ABCMeta, abstractmethod


class Scraper(metaclass=ABCMeta):
    """
    Base class for all scrapers/downloaders.
    """

    @abstractmethod
    def append_to_queue(self):
        pass
