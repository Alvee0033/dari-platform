#!/usr/bin/env python3
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ARTIFACTS_DIR = '/home/alvee/.gemini/antigravity/brain/d6932aff-aba6-4c34-9095-4cdca3db8b17'
CHROMEDRIVER_PATH = '/home/alvee/.cache/selenium/chromedriver/linux64/146.0.7680.165/chromedriver'

def create_driver(width=1920, height=1080):
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument(f'--window-size={width},{height}')
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=opts)

def run_tests():
    driver = create_driver(1920, 1080)
    print("=== Starting ADREC / DARI E2E Verification Suite ===")

    try:
        # TEST 1: Admin Dashboard Load & Metrics
        print("\n--- TEST 1: Admin Dashboard Load & Metrics ---")
        driver.get('http://localhost:8080/admin')
        time.sleep(1)

        assert "ADREC Admin" in driver.title, f"Unexpected title: {driver.title}"
        kpi_total = driver.find_element(By.ID, 'kpiTotalDocs').text
        kpi_active = driver.find_element(By.ID, 'kpiActiveDocs').text
        kpi_inactive = driver.find_element(By.ID, 'kpiInactiveDocs').text
        kpi_inquiries = driver.find_element(By.ID, 'kpiTotalInquiries').text
        
        print(f"KPIs Loaded: Total={kpi_total}, Active={kpi_active}, Inactive={kpi_inactive}, Inquiries={kpi_inquiries}")
        assert int(kpi_total) >= 8, f"Expected at least 8 docs, got {kpi_total}"

        # Capture Desktop Dashboard Screenshot
        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'admin_e2e_dashboard.png'))
        print("Captured admin_e2e_dashboard.png")

        # TEST 2: Register New Document via Admin UI
        print("\n--- TEST 2: Register New Document in Admin UI ---")
        btn_add = driver.find_element(By.ID, 'btnAddDocument')
        btn_add.click()
        time.sleep(0.5)

        # Fill modal form
        doc_num_inp = driver.find_element(By.ID, 'formDocNumber')
        doc_num_inp.clear()
        doc_num_inp.send_keys('UNT999111')

        party_inp = driver.find_element(By.ID, 'formPartyName')
        party_inp.clear()
        party_inp.send_keys('HAMDAN SULTAN AL-NAHYAN')

        unit_inp = driver.find_element(By.ID, 'formUnitPlot')
        unit_inp.clear()
        unit_inp.send_keys('PENTHOUSE-99')

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'admin_e2e_add_modal.png'))
        print("Captured admin_e2e_add_modal.png")

        # Submit form
        form = driver.find_element(By.ID, 'docEditForm')
        form.submit()
        time.sleep(1)

        # Verify new document is visible in table
        new_kpi_total = driver.find_element(By.ID, 'kpiTotalDocs').text
        assert int(new_kpi_total) == int(kpi_total) + 1, f"Expected {int(kpi_total)+1}, got {new_kpi_total}"
        assert "HAMDAN SULTAN AL-NAHYAN" in driver.page_source, "New document party not found in table"
        print("Successfully registered UNT999111 in Document Registry.")

        # TEST 3: Public Verification of the Newly Registered Document
        print("\n--- TEST 3: Public Verification of UNT999111 ---")
        driver.get('http://localhost:8080/en?app/verify-document')
        time.sleep(1)

        current_url = driver.current_url
        print(f"Public Portal URL: {current_url}")
        assert current_url == 'http://localhost:8080/en?app/verify-document', f"URL is not clean: {current_url}"

        # Click 'Verify Another Document' to display search input form
        btn_another = driver.find_element(By.ID, 'btnVerifyAnother')
        btn_another.click()
        time.sleep(0.5)

        # Enter UNT999111 into tenancy input
        tenancy_input = driver.find_element(By.ID, 'tenancyNumberInput')
        tenancy_input.clear()
        tenancy_input.send_keys('UNT999111')

        btn_submit = driver.find_element(By.CSS_SELECTOR, '#viewTenancy button[type="submit"]')
        btn_submit.click()
        time.sleep(1.8)

        # Check URL remains strictly clean
        current_url_after = driver.current_url
        print(f"URL after submit: {current_url_after}")
        assert current_url_after == 'http://localhost:8080/en?app/verify-document', f"URL modified: {current_url_after}"

        # Check Verified Result view
        res_view = driver.find_element(By.ID, 'verifyResultView')
        assert res_view.is_displayed(), "Verified result view is not displayed"
        
        party_rendered = driver.find_element(By.ID, 'resPartyValue').text
        status_rendered = driver.find_element(By.ID, 'resStatusText').text
        print(f"Result View Party: '{party_rendered}', Status: '{status_rendered}'")
        assert "HAMDAN SULTAN AL-NAHYAN" in party_rendered, f"Expected HAMDAN SULTAN AL-NAHYAN, got {party_rendered}"
        assert "active and verified" in status_rendered.lower(), f"Unexpected status: {status_rendered}"

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'public_verified_unt999111.png'))
        print("Captured public_verified_unt999111.png")

        # TEST 4: Expired Contract Verification (TC-2024-8890)
        print("\n--- TEST 4: Expired Contract Verification (TC-2024-8890) ---")
        btn_another_2 = driver.find_element(By.ID, 'btnVerifyAnother')
        btn_another_2.click()
        time.sleep(0.5)

        tenancy_input = driver.find_element(By.ID, 'tenancyNumberInput')
        tenancy_input.clear()
        tenancy_input.send_keys('TC-2024-8890')

        btn_submit = driver.find_element(By.CSS_SELECTOR, '#viewTenancy button[type="submit"]')
        btn_submit.click()
        time.sleep(1.8)

        # Check Not Found / Refused view for expired document
        nf_view = driver.find_element(By.ID, 'verifyNotFoundView')
        assert nf_view.is_displayed(), "Refused/Not found view is not displayed"
        
        nf_title = driver.find_element(By.ID, 'nfStatusText').text
        nf_desc = driver.find_element(By.ID, 'nfDetailsDesc').text
        print(f"Expired Doc Title: '{nf_title}'")
        print(f"Expired Doc Desc: '{nf_desc}'")
        assert "expired" in nf_title.lower(), f"Expected 'expired' in title, got: {nf_title}"
        assert "KHALID MOHAMMED AL-HOSANI" in nf_desc, f"Party name missing in description: {nf_desc}"

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'public_expired_refused.png'))
        print("Captured public_expired_refused.png")

        # TEST 5: Verify Admin Audit Stream Logged the Public Inquiries
        print("\n--- TEST 5: Verify Admin Audit Stream Updates ---")
        driver.get('http://localhost:8080/admin')
        time.sleep(1)

        audit_body = driver.find_element(By.ID, 'auditTableBody')
        audit_text = audit_body.text
        print("Top of Audit Stream:\n" + "\n".join(audit_text.splitlines()[:5]))
        assert "UNT999111" in audit_text, "UNT999111 search inquiry not logged in audit stream"
        assert "TC-2024-8890" in audit_text, "TC-2024-8890 search inquiry not logged in audit stream"
        print("Audit stream successfully tracked both public portal inquiries in real-time!")

        # TEST 6: Mobile Responsiveness & Overflow Check
        print("\n--- TEST 6: Mobile Viewport & 0-px Overflow Check ---")
        driver.set_window_size(390, 844)
        time.sleep(1)

        scroll_width = driver.execute_script("return document.documentElement.scrollWidth;")
        client_width = driver.execute_script("return document.documentElement.clientWidth;")
        print(f"Mobile (390px) ScrollWidth={scroll_width}, ClientWidth={client_width}")
        assert scroll_width <= client_width, f"Horizontal overflow detected: {scroll_width} > {client_width}"

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'admin_mobile_390.png'))
        print("Captured admin_mobile_390.png")

        # Check mobile public portal too
        driver.get('http://localhost:8080/en?app/verify-document')
        time.sleep(1)
        m_scroll = driver.execute_script("return document.documentElement.scrollWidth;")
        m_client = driver.execute_script("return document.documentElement.clientWidth;")
        print(f"Public Mobile ScrollWidth={m_scroll}, ClientWidth={m_client}")
        assert m_scroll <= m_client, f"Public mobile horizontal overflow: {m_scroll} > {m_client}"

        print("\nALL 6 VERIFICATION TEST SUITES PASSED FLAWLESSLY!")

    finally:
        driver.quit()

if __name__ == '__main__':
    run_tests()
