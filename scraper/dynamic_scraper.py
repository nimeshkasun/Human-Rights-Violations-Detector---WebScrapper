"""
Dynamic site scraper using Selenium (Chrome).
Used for JavaScript-heavy pages that don't render without a browser.
"""
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup

import config
from utils.logger import get_logger

logger = get_logger("hrv.scraper.dynamic")


def _build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(f"user-agent={config.USER_AGENT}")
    # Suppress selenium logs
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    # webdriver-manager is used to auto-download chromedriver
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except Exception:  # noqa: BLE001
        service = Service()  # rely on PATH
    return webdriver.Chrome(service=service, options=opts)


def fetch_page(url: str, headless: bool = True) -> Optional[BeautifulSoup]:
    """
    Load `url` in Chrome and return a BeautifulSoup of the rendered DOM.
    """
    driver = None
    settings = config.load_settings()
    headless = settings.get("chrome_headless", True)
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            driver = _build_driver(headless)
            driver.set_page_load_timeout(config.SELENIUM_TIMEOUT)
            driver.get(url)
            # Wait for body to be present
            WebDriverWait(driver, config.SELENIUM_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(config.PAGE_LOAD_DELAY)
            html = driver.page_source
            return BeautifulSoup(html, "html.parser")
        except TimeoutException:
            logger.warning("Selenium timeout on %s (attempt %d)", url, attempt)
        except WebDriverException as exc:
            logger.warning("WebDriver error on %s (attempt %d): %s", url, attempt, exc)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:  # noqa: BLE001
                    pass
                driver = None
        time.sleep(2 ** attempt)
    logger.error("Failed to fetch (dynamic) %s after %d attempts.", url, config.MAX_RETRIES)
    return None


def extract_articles(soup: BeautifulSoup, source_url: str) -> list[dict]:
    """Reuse the same heuristic extractor from static_scraper."""
    from scraper.static_scraper import extract_articles as _extract
    return _extract(soup, source_url)
