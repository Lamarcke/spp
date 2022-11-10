from selenium.webdriver.common.by import By
from selenium.webdriver.ie.webdriver import WebDriver


class ScraperHelper:

    @staticmethod
    def monitor_downloads(driver: WebDriver, handle: str):
        """
        Checks for failed downloads and resume them.
        Receives a driver parameter.
        The handle parameter determines the window in which to watch for chrome downloads.
        Get it using driver.window_handlers.

        """

        download_url = "chrome://downloads/"

        if driver.current_url != handle:
            driver.switch_to.window(handle)

        if driver.current_url != download_url:
            driver.get(download_url)
        download_elements = driver.find_elements(By.CSS_SELECTOR, "cr-button")

        for el in download_elements:
            if el.text.find("Retomar") != -1 or el.text.find("Tentar novamente") != -1:
                el.click()



