import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = os.getenv("NYAYA_BASE_URL", "http://127.0.0.1:5000")

@pytest.fixture
def base_url():
    return BASE_URL

@pytest.fixture
def driver():
    opts = Options()
    opts.add_argument("--window-size=1366,768")
    if os.getenv("HEADLESS") == "1":
        opts.add_argument("--headless=new")
    d = webdriver.Chrome(options=opts)
    yield d
    d.quit()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        d = item.funcargs.get("driver")
        if d:
            os.makedirs("tests/screenshots", exist_ok=True)
            d.save_screenshot(f"tests/screenshots/{item.name}.png")