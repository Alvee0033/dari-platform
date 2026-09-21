import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def run_tests():
    base_url = "http://efuxksvqqtpcpncnapl3nrzr.163.227.239.97.sslip.io"
    print(f"Testing live URL: {base_url}")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,950")

    driver = webdriver.Chrome(options=opts)

    try:
        # 1. Unauthenticated access to /admin must redirect to /login
        print("[TEST 1] Accessing /admin without auth...")
        driver.get(f"{base_url}/admin")
        time.sleep(2)
        current_url = driver.current_url
        print(f"  Current URL: {current_url}")
        assert "/login" in current_url, f"Expected redirect to /login, got: {current_url}"
        print("  ✓ Unauthenticated user redirected to dedicated /login page.")

        # 2. Login through /login page
        print("[TEST 2] Logging in through /login...")
        email_inp = driver.find_element(By.ID, "loginEmail")
        pwd_inp = driver.find_element(By.ID, "loginPassword")
        submit_btn = driver.find_element(By.ID, "btnLoginSubmit")

        email_inp.clear()
        email_inp.send_keys("officer@adrec.gov.ae")
        pwd_inp.clear()
        pwd_inp.send_keys("admin123")
        submit_btn.click()
        time.sleep(3)

        assert "/admin" in driver.current_url, f"Expected /admin after login, got: {driver.current_url}"
        print("  ✓ Successfully authenticated and redirected to /admin.")

        # 3. Open contract modal and verify all 8 contract page images load with positive dimensions
        print("[TEST 3] Testing contract modal and 8-page images...")
        time.sleep(2)
        contract_btns = driver.find_elements(By.CSS_SELECTOR, "button.contract")
        assert len(contract_btns) > 0, "No contract preview buttons found"
        contract_btns[0].click()
        time.sleep(4)

        modal = driver.find_element(By.ID, "contractModalOverlay")
        assert "active" in modal.get_attribute("class"), "Contract modal not open"
        
        # Take screenshot of open modal to save as artifact
        driver.save_screenshot("/home/alvee/Desktop/dari/screenshots/verified_contract_preview.png")

        imgs = driver.find_elements(By.CSS_SELECTOR, ".contract-page-img")
        print(f"  Found {len(imgs)} contract page images in modal.")
        assert len(imgs) == 8, f"Expected 8 images, found {len(imgs)}"

        for i, img in enumerate(imgs, 1):
            w = driver.execute_script("return arguments[0].naturalWidth;", img)
            h = driver.execute_script("return arguments[0].naturalHeight;", img)
            src = img.get_attribute("src")
            print(f"    Page {i}: {w}x{h}px from {src}")
            assert w > 0 and h > 0, f"Page {i} image failed to load (dimensions {w}x{h})"

        print("  ✓ All 8 contract page images loaded and rendered perfectly!")

        # 4. Test Logout
        print("[TEST 4] Testing logout...")
        logout_btn = driver.find_element(By.ID, "btnLogoutNav")
        logout_btn.click()
        time.sleep(2)
        assert "/login" in driver.current_url, f"Expected /login after logout, got: {driver.current_url}"
        print("  ✓ Logout successful and redirected back to /login.")

        print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_tests()
