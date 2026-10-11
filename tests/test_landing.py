def test_landing_page_loads(driver, base_url):
    driver.get(base_url)
    assert "Nyaya" in driver.page_source