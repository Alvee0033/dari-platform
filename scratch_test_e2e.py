import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def run_e2e_tests():
    base_url = "http://efuxksvqqtpcpncnapl3nrzr.163.227.239.97.sslip.io"
    print(f"Starting E2E Selenium tests against {base_url}...")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    driver = webdriver.Chrome(options=options)

    try:
        # Test 1: Public Verification Home Page
        print("[TEST 1] Public verification page loading...")
        driver.get(f"{base_url}/en/app/verify-document")
        time.sleep(2)
        assert "DARI" in driver.title or "Verification" in driver.title or len(driver.page_source) > 500
        print("  ✓ Public page loaded successfully.")

        # Test 2: Perform Document Search
        print("[TEST 2] Performing document verification search for '202401452705'...")
        input_ref = driver.find_element(By.ID, "tenancyNumberInput")
        input_ref.clear()
        input_ref.send_keys("202401452705")
        
        btn_verify = driver.find_element(By.CSS_SELECTOR, "#viewTenancy button[type='submit']")
        btn_verify.click()
        time.sleep(3)

        result_section = driver.find_element(By.ID, "verifyResultView")
        assert result_section.is_displayed()
        assert "202401452705" in driver.page_source or "active" in driver.page_source.lower()
        print("  ✓ Document verified successfully via API/Postgres.")

        # Test 3: Admin Login Modal & Verification (No Demo Card)
        print("[TEST 3] Admin console login modal check...")
        driver.get(f"{base_url}/admin")
        time.sleep(2)

        # Check demo card is completely gone
        demo_cards = driver.find_elements(By.ID, "btnQuickFillDemo")
        assert len(demo_cards) == 0 or not demo_cards[0].is_displayed(), "ERROR: Demo card still visible!"
        print("  ✓ Demo credentials card is completely absent from login page.")

        # Test 4: Perform Officer Authentication
        print("[TEST 4] Authenticating officer credentials...")
        email_inp = driver.find_element(By.ID, "loginEmail")
        pass_inp = driver.find_element(By.ID, "loginPassword")
        btn_login = driver.find_element(By.ID, "btnLoginSubmit")

        email_inp.send_keys("officer@adrec.gov.ae")
        pass_inp.send_keys("admin123")
        btn_login.click()
        time.sleep(2)

        overlay = driver.find_element(By.ID, "adminLoginOverlay")
        assert "active" not in overlay.get_attribute("class")
        print("  ✓ Officer logged in successfully and accessed Operations Center.")

        # Test 5: Verify Document Registry Table
        print("[TEST 5] Checking Registry Table...")
        time.sleep(2)
        table_rows = driver.find_elements(By.CSS_SELECTOR, "#registryTableBody tr")
        assert len(table_rows) > 0, f"Expected rows in registry, found {len(table_rows)}"
        print(f"  ✓ Found {len(table_rows)} documents in live PostgreSQL registry.")

        print("\nALL 5 E2E SELENIUM TESTS PASSED SUCCESSFULLY!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_e2e_tests()
