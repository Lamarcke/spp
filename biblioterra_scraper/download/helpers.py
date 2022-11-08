from selenium.webdriver.common.by import By
from selenium.webdriver.ie.webdriver import WebDriver


class ScraperHelper:

    @staticmethod
    def monitor_downloads(driver: WebDriver):
        """
        Checks for failed downloads and resume them.
        """
        download_url = "chrome://downloads/"
        if driver.current_url != download_url:
            driver.get(download_url)
        download_elements = driver.find_elements(By.CSS_SELECTOR, "cr-button")
        for el in download_elements:
            if el.text.find("Continuar"):
                el.click()



