import re

def test_c_level_full_flow(page):
    page.goto("http://localhost:8501", timeout=60000)

    #---------------------------------------
    # ---------- Login as C-level ----------
    #---------------------------------------
    page.get_by_role("textbox", name="Username").fill("admin")
    page.get_by_role("textbox", name="Password").fill("admin123")
    page.get_by_role("button", name="Login").click()
    page.wait_for_selector("text=You have global access", timeout=10000)

    # ---------- Switch to C-Level Admin Tab ----------
    page.get_by_role("tab", name="👤 Admin (C-Level)").click()
    page.get_by_role("heading", name="Create New Role")
    
    #---------------------------------------
    # ---------- Create Role ----------
    #---------------------------------------
    page.get_by_text("New Role Name")
    page.get_by_role("textbox", name="New Role Name").fill("QA Team")
    page.get_by_role("button", name="Add Role").click()
    page.wait_for_selector("text=Role 'QA Team' created", timeout=15000)

    page.wait_for_timeout(15000)
    
    #---------------------------------------
    # ---------- Create User ----------
    #---------------------------------------
    page.get_by_role("heading", name="Add User").wait_for(timeout=15000)
    page.get_by_text("New Username")
    page.get_by_role("textbox", name="New Username").fill("qa_user")
    page.get_by_text("New Password")
    page.get_by_role("textbox", name="New Password").fill("qa_pass")
    page.get_by_text("Assign Role")
    # Wait for and select the role from Streamlit's fake dropdown
    dropdown = page.get_by_role("combobox")#, name="Select Role")
    dropdown.wait_for(timeout=15000)
    dropdown.click()

    dropdown_popup = page.get_by_test_id("stSelectboxVirtualDropdown")
    dropdown_popup.get_by_text("QA Team", exact=True).click()
    # Select option by visible text
    #page.get_by_text("QA Team").click()
    #page.get_by_role("combobox", name="Select Role").select_option("QA Team")  # Assumes labeled combobox
    page.get_by_role("button", name="Create User").click()
    page.wait_for_selector("text=User 'qa_user' added", timeout=15000)
    
    
    #---------------------------------------
    # ---------- Upload Document ----------
    #---------------------------------------
    page.get_by_role("tab", name="🧾 Upload (C-Level)").click()
    page.get_by_text("Select document access role")
    # Choose role for document access

    dropdown = page.get_by_role("combobox")#, name="Select Role")
    dropdown.wait_for(timeout=15000)
    dropdown.click()

    # Select "QA Team" or "C-Level" from dropdown using virtual dropdown container
    dropdown_popup = page.get_by_test_id("stSelectboxVirtualDropdown")
    dropdown_popup.get_by_text("C-Level", exact=True).click()
    dropdown.wait_for(timeout=15000)

    page.get_by_text("Upload document (.md or .csv)")

    # Simulate file upload
    # Wait for upload area
    page.get_by_test_id("stFileUploaderDropzone").wait_for(timeout=5000)

# Upload markdown file
    page.locator('input[type="file"]').set_input_files("tests/sample_docs/sample_hr.md")

    #page.get_by_test_id("stFileUploaderDropzone").set_input_files("tests/sample_docs/sample_hr.md")
    dropdown.wait_for(timeout=15000)
    
    #page.get_by_role("combobox", name="Select Role for Document").select_option("QA Team")
    
    page.get_by_role("button", name="Upload Document").click()
    page.wait_for_timeout(15000)
    page.wait_for_selector("text=sample_hr.md uploaded successfully for role 'c-level'", timeout=15000)

    # ---------- Logout ----------
    page.get_by_role("button", name="Logout").click()
    page.wait_for_selector("text=Login", timeout=15000)
    

    #---------------------------------------
    # Login with newly created user
    #---------------------------------------
    page.get_by_role("textbox", name="Username").fill("qa_user")
    page.get_by_role("textbox", name="Password").fill("qa_pass")
    page.get_by_role("button", name="Login").click()

    # Validate role-specific access (QA Team, no C-level privileges)
    page.wait_for_selector("text=You have access to documents and features related", timeout=15000)
    page.wait_for_selector("text=You also have access to General documents (e.g., company policies, holidays, announcements)")
    
    # Assert C-Level only tabs are not visible to regular user
    assert page.locator('text=👤 Admin (C-Level)').count() == 0
    assert page.locator('text=🧾 Upload (C-Level)').count() == 0

    # Ask a question
    page.get_by_role("heading", name="Ask a question")
    page.get_by_text("Your question")
    page.get_by_role("textbox",name="Your question").fill("Tell me something")
    page.get_by_role("button", name="Submit").click()

    # Wait for response
    page.wait_for_selector("text=Answer:", timeout=10000)

    # Logout
    page.get_by_role("button", name="Logout").click()
    page.wait_for_selector("text=Login", timeout=15000)
    
    #---------------------------------------
    # Attempt login with incorrect credentials
    #---------------------------------------
    page.get_by_role("textbox", name="Username").fill("Tony")
    page.get_by_role("textbox", name="Password").fill("wrongpassword")
    page.get_by_role("button", name="Login").click()

    # Expect an error message or no redirect
    page.wait_for_selector("text=Invalid credentials", timeout=5000)
    
