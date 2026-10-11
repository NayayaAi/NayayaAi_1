import os
import pytest
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.pages.login_page import LoginPage


def test_empty_fields_show_validation_message(driver, base_url):
    page = LoginPage(driver, base_url).open()
    page.click_submit()
    assert "fill in all fields" in page.message_text().lower()


def test_wrong_credentials_show_error(driver, base_url):
    page = LoginPage(driver, base_url).open()
    page.login("wrong@example.com", "wrongpass123")
    assert page.message_text() != ""
    assert "/login" in driver.current_url


def test_protected_page_redirects_when_logged_out(driver, base_url):
    driver.get(f"{base_url}/citizen_dashboard")
    WebDriverWait(driver, 10).until(EC.url_contains("login"))


@pytest.mark.skipif(not os.getenv("TEST_EMAIL"), reason="TEST_EMAIL not set")
def test_valid_citizen_login_redirects(driver, base_url):
    page = LoginPage(driver, base_url).open()
    page.login(os.environ["TEST_EMAIL"], os.environ["TEST_PASSWORD"])
    assert "login successful" in page.message_text().lower()
    WebDriverWait(driver, 10).until(EC.url_contains("citizen-dashboard"))
