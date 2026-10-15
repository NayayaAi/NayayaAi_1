from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginPage:
    EMAIL = (By.ID, "email")
    PASSWORD = (By.ID, "password")
    SUBMIT = (By.CSS_SELECTOR, "button.btn")
    MESSAGE = (By.CSS_SELECTOR, "#msg p")

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)

    def open(self):
        self.driver.get(f"{self.base_url}/login")
        return self

    def login(self, email, password):
        self.wait.until(EC.visibility_of_element_located(self.EMAIL)).send_keys(email)
        self.driver.find_element(*self.PASSWORD).send_keys(password)
        self.driver.find_element(*self.SUBMIT).click()

    def click_submit(self):
        self.wait.until(EC.element_to_be_clickable(self.SUBMIT)).click()

    def message_text(self):
        return self.wait.until(EC.visibility_of_element_located(self.MESSAGE)).text
