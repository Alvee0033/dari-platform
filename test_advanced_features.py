#!/usr/bin/env python3
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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

def run():
    print("=== Starting Batch Actions, Mobile-First UI & Settings Verification Suite ===")
    driver = create_driver(1920, 1080)

    try:
        # TEST 1: Reset seed to known state and verify UI
        print("\n--- TEST 1: Load Admin & Check Elements ---")
        driver.get('http://localhost:8080/admin')
        time.sleep(1)

        # Reset seed via direct localStorage clear for clean test run
        driver.execute_script("localStorage.removeItem('dari_registry_v1'); localStorage.removeItem('dari_admin_settings_v1');")
        driver.refresh()
        time.sleep(1)

        total_docs = driver.find_element(By.ID, 'kpiTotalDocs').text
        print(f"Total documents loaded: {total_docs}")
        assert int(total_docs) >= 8, f"Expected at least 8 docs, got {total_docs}"

        # TEST 2: Multi-Selection & Floating Batch Actions Bar
        print("\n--- TEST 2: Multi-Selection & Batch Actions Bar ---")
        checkboxes = driver.find_elements(By.CSS_SELECTOR, '.doc-row-checkbox')
        assert len(checkboxes) >= 3, "Not enough checkboxes found"

        # Check first 2 documents
        driver.execute_script("arguments[0].click();", checkboxes[0])
        driver.execute_script("arguments[0].click();", checkboxes[1])
        time.sleep(0.5)

        batch_bar = driver.find_element(By.ID, 'batchActionsBar')
        assert "active" in batch_bar.get_attribute("class"), "Batch actions bar did not activate"
        
        count_text = driver.find_element(By.ID, 'batchSelectedCount').text
        print(f"Selected count in floating bar: {count_text}")
        assert count_text == "2", f"Expected 2 selected, got {count_text}"

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'admin_batch_bar_active.png'))
        print("Captured admin_batch_bar_active.png")

        # Test Batch Mark as Expired
        print("Testing Batch 'Mark Expired'...")
        btn_batch_expire = driver.find_element(By.ID, 'btnBatchExpire')
        driver.execute_script("arguments[0].click();", btn_batch_expire)
        time.sleep(0.8)

        toast = driver.find_element(By.ID, 'adminToast').text
        print(f"Toast output: {toast}")
        assert "Marked 2 documents as Expired" in toast, f"Unexpected toast: {toast}"

        # TEST 3: Batch Delete Selection
        print("\n--- TEST 3: Multi-Delete Selection & Modal Confirmation ---")
        # Click select all checkbox
        select_all = driver.find_element(By.ID, 'selectAllCheckbox')
        driver.execute_script("arguments[0].click();", select_all)
        time.sleep(0.5)

        count_all = driver.find_element(By.ID, 'batchSelectedCount').text
        print(f"Select All count: {count_all}")
        assert int(count_all) >= 8, f"Expected all selected, got {count_all}"

        # Deselect all
        btn_deselect = driver.find_element(By.ID, 'btnBatchDeselect')
        driver.execute_script("arguments[0].click();", btn_deselect)
        time.sleep(0.5)

        # Select exactly 2 documents to delete
        checkboxes = driver.find_elements(By.CSS_SELECTOR, '.doc-row-checkbox')
        driver.execute_script("arguments[0].click();", checkboxes[1])
        driver.execute_script("arguments[0].click();", checkboxes[2])
        time.sleep(0.5)

        btn_batch_delete = driver.find_element(By.ID, 'btnBatchDelete')
        driver.execute_script("arguments[0].click();", btn_batch_delete)
        time.sleep(0.5)

        batch_modal = driver.find_element(By.ID, 'batchDeleteModalOverlay')
        assert "active" in batch_modal.get_attribute("class"), "Batch delete modal did not open"
        
        count_label = driver.find_element(By.ID, 'batchDeleteCountLabel').text
        print(f"Batch Delete modal count: {count_label}")
        assert count_label == "2", f"Expected 2 in modal count, got {count_label}"

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'admin_batch_delete_modal.png'))
        print("Captured admin_batch_delete_modal.png")

        # Confirm Batch Delete
        btn_confirm_batch = driver.find_element(By.ID, 'btnConfirmBatchDelete')
        driver.execute_script("arguments[0].click();", btn_confirm_batch)
        time.sleep(1)

        after_total = driver.find_element(By.ID, 'kpiTotalDocs').text
        print(f"Total documents after batch delete: {after_total}")
        assert int(after_total) == int(total_docs) - 2, f"Expected {int(total_docs)-2}, got {after_total}"

        # TEST 4: Settings & Password Changer
        print("\n--- TEST 4: Settings, Email & Password Changer ---")
        btn_settings = driver.find_element(By.ID, 'btnOpenSettings')
        driver.execute_script("arguments[0].click();", btn_settings)
        time.sleep(0.6)

        settings_modal = driver.find_element(By.ID, 'settingsModalOverlay')
        assert "active" in settings_modal.get_attribute("class"), "Settings modal did not open"

        # Update Display Name, Email, and Role
        name_inp = driver.find_element(By.ID, 'settingDisplayName')
        name_inp.clear()
        name_inp.send_keys('Eng. Hamdan Al-Zaabi')

        email_inp = driver.find_element(By.ID, 'settingEmail')
        email_inp.clear()
        email_inp.send_keys('hamdan.zaabi@adrec.gov.ae')

        role_inp = driver.find_element(By.ID, 'settingRole')
        role_inp.clear()
        role_inp.send_keys('Chief Regulatory Officer')

        # Switch to Tab 2: Change Password
        tab_pwd = driver.find_element(By.CSS_SELECTOR, '.settings-tab-btn[data-tab="tabPassword"]')
        driver.execute_script("arguments[0].click();", tab_pwd)
        time.sleep(0.4)

        # Test Password strength meter and inputs
        cur_pwd_inp = driver.find_element(By.ID, 'settingCurrentPassword')
        cur_pwd_inp.send_keys('admin123')

        new_pwd_inp = driver.find_element(By.ID, 'settingNewPassword')
        new_pwd_inp.send_keys('Adrec@2026Secure!')

        confirm_pwd_inp = driver.find_element(By.ID, 'settingConfirmPassword')
        confirm_pwd_inp.send_keys('Adrec@2026Secure!')

        strength_label = driver.find_element(By.ID, 'pwdStrengthLabel').text
        print(f"Password Strength: {strength_label}")
        assert "Strong" in strength_label, f"Expected strong password, got: {strength_label}"

        # Toggle password eye
        eye_btn = driver.find_element(By.CSS_SELECTOR, '.btn-toggle-password[data-target="settingNewPassword"]')
        driver.execute_script("arguments[0].click();", eye_btn)
        assert new_pwd_inp.get_attribute("type") == "text", "Eye toggle did not unmask password"
        driver.execute_script("arguments[0].click();", eye_btn)
        assert new_pwd_inp.get_attribute("type") == "password", "Eye toggle did not re-mask password"

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'admin_settings_modal.png'))
        print("Captured admin_settings_modal.png")

        # Submit settings form
        settings_form = driver.find_element(By.ID, 'settingsForm')
        driver.execute_script("arguments[0].requestSubmit();", settings_form)
        time.sleep(1)

        # Verify header reflects new profile
        nav_name = driver.find_element(By.ID, 'navUserName').text
        nav_role = driver.find_element(By.ID, 'navUserRole').text
        nav_avatar = driver.find_element(By.ID, 'navAvatarInitials').text

        print(f"Updated Profile: Name='{nav_name}', Role='{nav_role}', Avatar='{nav_avatar}'")
        assert nav_name == 'Eng. Hamdan Al-Zaabi', f"Name not updated: {nav_name}"
        assert nav_role == 'Chief Regulatory Officer', f"Role not updated: {nav_role}"
        assert nav_avatar == 'EH', f"Avatar initials not updated: {nav_avatar}"

        # TEST 5: Mobile-First UI & Responsive Cards
        print("\n--- TEST 5: Mobile-First UI (390px Viewport) ---")
        driver.set_window_size(390, 844)
        time.sleep(1)

        # Verify Mobile Bottom Navigation is displayed
        bottom_nav = driver.find_element(By.ID, 'adminMobileBottomNav')
        assert bottom_nav.is_displayed(), "Mobile bottom navigation not displayed on 390px"

        # Verify Mobile Cards list is displayed
        cards_list = driver.find_element(By.ID, 'mobileDocCardsList')
        assert cards_list.is_displayed(), "Mobile document cards list not displayed"
        
        cards = driver.find_elements(By.CSS_SELECTOR, '.mobile-doc-card')
        print(f"Mobile Document Cards rendered: {len(cards)}")
        assert len(cards) >= 6, f"Expected at least 6 mobile cards, got {len(cards)}"

        # Check select on mobile card
        card_chk = cards[0].find_element(By.CSS_SELECTOR, '.doc-row-checkbox')
        driver.execute_script("arguments[0].click();", card_chk)
        time.sleep(0.5)

        m_batch_bar = driver.find_element(By.ID, 'batchActionsBar')
        assert "active" in m_batch_bar.get_attribute("class"), "Batch bar did not activate on mobile card click"

        # Check 0-px horizontal overflow on mobile
        sw = driver.execute_script("return document.documentElement.scrollWidth;")
        cw = driver.execute_script("return document.documentElement.clientWidth;")
        print(f"Mobile Viewport Check: scrollWidth={sw}, clientWidth={cw}")
        assert sw <= cw, f"Mobile horizontal overflow: {sw} > {cw}"

        driver.save_screenshot(os.path.join(ARTIFACTS_DIR, 'admin_mobile_first_ui.png'))
        print("Captured admin_mobile_first_ui.png")

        print("\nALL 5 ADVANCED VERIFICATION TESTS PASSED FLAWLESSLY!")

    finally:
        driver.quit()

if __name__ == '__main__':
    run()
