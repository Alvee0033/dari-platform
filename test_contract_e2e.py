#!/usr/bin/env python3
"""
End-to-End Selenium Verification Test for:
1. Contract Generation API & Streaming (PDF + 9 PNG pages)
2. Admin Operations Center: 9-Page Carousel Preview Modal, Thumbnail Strip, Zoom, and Merged PDF Download
3. Public DARI Verification Portal: Verification flow for contract 202401452705, results display, and Official Contract PDF Download button
"""

import os
import sys
import time
import json
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://localhost:8080"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doc_gen", "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_api_generation():
    print("\n--- 1. Testing API Endpoints ---")
    
    # 1.1 POST /api/generate-contract
    req = urllib.request.Request(
        f"{BASE_URL}/api/generate-contract",
        data=json.dumps({"documentNumber": "202401452705"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"POST generate-contract returned {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        print(f"✓ POST /api/generate-contract success: {data.get('contractNumber')}, pages={data.get('pageCount')}")
        assert data.get("pageCount") == 9
        assert len(data.get("pages")) == 9

    # 1.2 GET /api/contracts/202401452705.pdf
    with urllib.request.urlopen(f"{BASE_URL}/api/contracts/202401452705.pdf", timeout=10) as resp:
        assert resp.status == 200
        ct = resp.headers.get("Content-Type")
        cl = int(resp.headers.get("Content-Length", 0))
        assert "application/pdf" in ct, f"Expected PDF content type, got {ct}"
        assert cl > 500000, f"PDF file size too small: {cl} bytes"
        print(f"✓ GET /api/contracts/202401452705.pdf returned {cl} bytes, Content-Type={ct}")

    # 1.3 GET Page images 1 to 9
    for p in range(1, 10):
        with urllib.request.urlopen(f"{BASE_URL}/api/contracts/202401452705/{p}.png", timeout=10) as resp:
            assert resp.status == 200
            ct = resp.headers.get("Content-Type")
            assert "image/png" in ct
    print("✓ All 9 page PNGs streamed successfully")


def test_admin_dashboard(driver):
    print("\n--- 2. Testing Admin Dashboard Contract Modal & Carousel ---")
    driver.set_window_size(1400, 1000)
    driver.get(f"{BASE_URL}/admin")

    wait = WebDriverWait(driver, 10)
    
    # Wait for registry table to render
    wait.until(EC.presence_of_element_located((By.ID, "registryTableBody")))
    time.sleep(1)

    # Find the row for contract 202401452705
    ref_cells = driver.find_elements(By.CLASS_NAME, "doc-ref-num")
    target_row = None
    for cell in ref_cells:
        if "202401452705" in cell.text:
            target_row = cell.find_element(By.XPATH, "./ancestor::tr")
            break

    assert target_row is not None, "Could not find row for contract 202401452705 in table"
    print(f"✓ Found contract 202401452705 in registry table")

    # Find and click the Contract action button
    contract_btn = target_row.find_element(By.CSS_SELECTOR, ".btn-icon-action.contract")
    assert contract_btn is not None, "Contract action button missing on tenancy row"
    contract_btn.click()
    print("✓ Clicked 'Generate & View Official Contract' button")

    # Verify modal is open and active
    modal = wait.until(EC.visibility_of_element_located((By.ID, "contractModalOverlay")))
    assert "active" in modal.get_attribute("class"), "Modal overlay should have class 'active'"

    # Check title and meta
    doc_num_el = driver.find_element(By.ID, "contractModalDocNum")
    status_el = driver.find_element(By.ID, "contractModalStatus")
    page_num_el = driver.find_element(By.ID, "contractCurrentPageNum")
    viewer_img = driver.find_element(By.ID, "contractViewerImage")

    assert doc_num_el.text == "202401452705"
    assert status_el.text == "Active"
    assert page_num_el.text == "1"

    # Wait for image to load
    time.sleep(1.5)
    img_natural_w = driver.execute_script("return arguments[0].naturalWidth;", viewer_img)
    assert img_natural_w > 0, "Page 1 image failed to load"
    print(f"✓ Page 1 loaded in stage viewer (naturalWidth={img_natural_w})")

    # Save screenshot of Page 1
    p1_shot = os.path.join(OUTPUT_DIR, "admin_contract_page_1.png")
    driver.save_screenshot(p1_shot)
    print(f"✓ Saved screenshot: {p1_shot}")

    # Click Next Page button -> Page 2
    next_btn = driver.find_element(By.ID, "btnContractNextPage")
    next_btn.click()
    time.sleep(1)
    assert page_num_el.text == "2"
    img_natural_w2 = driver.execute_script("return arguments[0].naturalWidth;", viewer_img)
    assert img_natural_w2 > 0
    print(f"✓ Page 2 navigated and rendered (naturalWidth={img_natural_w2})")

    # Click Thumbnail Pill for Page 9
    p9_thumb = driver.find_element(By.CSS_SELECTOR, "#contractThumbnailsStrip button[data-page='9']")
    p9_thumb.click()
    time.sleep(1)
    assert page_num_el.text == "9"
    img_natural_w9 = driver.execute_script("return arguments[0].naturalWidth;", viewer_img)
    assert img_natural_w9 > 0
    print(f"✓ Page 9 (Signatures) jumped via thumbnail pill (naturalWidth={img_natural_w9})")

    # Save screenshot of Page 9
    p9_shot = os.path.join(OUTPUT_DIR, "admin_contract_page_9.png")
    driver.save_screenshot(p9_shot)
    print(f"✓ Saved screenshot: {p9_shot}")

    # Verify Download links
    header_dl = driver.find_element(By.ID, "btnContractDownloadPdf")
    footer_dl = driver.find_element(By.ID, "btnContractFooterDownload")
    assert "202401452705.pdf" in header_dl.get_attribute("href")
    assert "202401452705.pdf" in footer_dl.get_attribute("href")
    print(f"✓ Verified download links point to official PDF: {header_dl.get_attribute('href')}")

    # Test Zoom Toggle
    zoom_btn = driver.find_element(By.ID, "btnContractZoomToggle")
    stage = driver.find_element(By.ID, "contractPageStage")
    zoom_btn.click()
    time.sleep(0.3)
    assert "zoomed" in stage.get_attribute("class")
    zoom_btn.click()
    time.sleep(0.3)
    assert "zoomed" not in stage.get_attribute("class")
    print("✓ Zoom/Fit toggle functional")

    # Close modal
    close_btn = driver.find_element(By.ID, "btnCloseContractModal")
    close_btn.click()
    time.sleep(0.5)
    assert "active" not in modal.get_attribute("class")
    print("✓ Modal closed successfully")


def test_public_verification(driver):
    print("\n--- 3. Testing Public Verification Portal ---")
    driver.set_window_size(1280, 960)
    driver.get(f"{BASE_URL}/en?app/verify-document")

    wait = WebDriverWait(driver, 10)
    
    # Wait for Tenancy tab input
    inp = wait.until(EC.visibility_of_element_located((By.ID, "tenancyNumberInput")))
    inp.clear()
    inp.send_keys("202401452705")
    print("✓ Entered contract number 202401452705")

    # Submit verification
    submit_btn = driver.find_element(By.CSS_SELECTOR, "#viewTenancy button[type='submit']")
    submit_btn.click()
    print("✓ Clicked 'Verify' button")

    # Wait for Result Card to be visible
    result_view = wait.until(EC.visibility_of_element_located((By.ID, "verifyResultView")))
    time.sleep(1.5)

    # Check Verified content
    status_text = driver.find_element(By.ID, "resStatusText").text
    party_val = driver.find_element(By.ID, "resPartyValue").text
    unit_val = driver.find_element(By.ID, "resUnitValue").text
    usage_val = driver.find_element(By.ID, "resUsageValue").text

    assert "Tenancy contract is active and verified" in status_text, f"Unexpected status text: {status_text}"
    assert "RANGITH RAMALINGAM" in party_val, f"Unexpected tenant: {party_val}"
    assert "Flat No. 606" in unit_val, f"Unexpected unit: {unit_val}"
    assert "Residential" in usage_val, f"Unexpected usage: {usage_val}"
    print(f"✓ Verification Result verified: Status='{status_text}', Tenant='{party_val}', Unit='{unit_val}'")

    # Check Download Official Contract (PDF) button
    pdf_row = driver.find_element(By.ID, "tenancyPdfDownloadRow")
    assert pdf_row.is_displayed(), "Official Tenancy Contract PDF download row is not displayed"
    pdf_btn = driver.find_element(By.ID, "btnDownloadVerifiedContractPdf")
    pdf_href = pdf_btn.get_attribute("href")
    assert "202401452705.pdf" in pdf_href, f"Unexpected PDF link: {pdf_href}"
    print(f"✓ Official Contract PDF download button verified: href='{pdf_href}', text='{pdf_btn.text}'")

    # Save screenshot of public verified view
    pub_shot = os.path.join(OUTPUT_DIR, "public_contract_verified_result.png")
    driver.save_screenshot(pub_shot)
    print(f"✓ Saved screenshot: {pub_shot}")


def main():
    test_api_generation()

    chrome_opts = Options()
    chrome_opts.add_argument("--headless")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1400,1000")

    driver = webdriver.Chrome(options=chrome_opts)
    try:
        test_admin_dashboard(driver)
        test_public_verification(driver)
        print("\n========================================================")
        print("🎉 ALL END-TO-END CONTRACT & VERIFICATION TESTS PASSED!")
        print("========================================================\n")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
