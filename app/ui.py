import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import base64

API_URL = "http://localhost:8000"

st.set_page_config(page_title="FinSolve Data Assistant", page_icon="🤖",layout="wide")
# -------------------------
# BACKGROUND IMAGES
# -------------------------
def set_bg_from_local(image_path):
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()

    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

set_bg_from_local("static/images/background.jpg")
# Two-column layout
left_col, right_col = st.columns([7,1])

with left_col:
    st.markdown("""
    <div style="background-color: rgba(255, 255, 255, 0.85); 
        padding: 5px; border-radius: 5px; box-shadow: 0px 0px 10px gray;
        text-align: center;">
        <h2>Welcome to FinSight</h2>
        <p>Your Document Assistant to get insights about Finsolve Technologies.</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------
# SESSION INIT
# -------------------------
if "auth" not in st.session_state:
    st.session_state.auth = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# Load roles into session state if not present
def fetch_roles():
    try:
        role_res = requests.get(f"{API_URL}/roles", auth=HTTPBasicAuth(*st.session_state.auth))
        return role_res.json().get("roles", [])
    except:
        return []


# -------------------------
# LOGIN PAGE
# -------------------------
if st.session_state.page == "login":
    st.markdown("",unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
   
        res = requests.get(f"{API_URL}/login", auth=HTTPBasicAuth(username, password))
        if res.status_code == 200:
            st.session_state.auth = (username, password)
            st.session_state.username = username
            st.session_state.password = password
            st.session_state.role = res.json()["role"]
        
            # Fetch roles once login is successful
            st.session_state.roles = fetch_roles()

            st.session_state.page = "main"  # Navigate to main app
            st.rerun()
        else:
            try:
                st.error(res.json().get("detail", "Login failed."))
            except:
                st.error("Server error. Please check FastAPI logs.")



# -------------------------
# MAIN APP AFTER LOGIN
# -------------------------
if st.session_state.page == "main":
    username = st.session_state.username
    role = st.session_state.role

    with right_col:
        st.markdown(f"**👤 User:** `{username}`  \n**🛡️ Role:** `{role}`")
        # --- Logout ---
        if st.button("🚪 Logout"):
            st.session_state.auth = None
            st.session_state.role = None
            st.session_state.page = "login"
            st.rerun()
    
        # Role-specific section
        # Dynamic rendering
    with left_col:
        st.markdown("")
        if role == "C-Level":
            st.write("You have global access")
            tab1, tab2, tab3 = st.tabs(["💬 Chat", "🧾 Upload (C-Level)", "👤 Admin (C-Level)"])
        
        elif role == "General":
            st.write(f"You have access to documents and features related to the `{role}` role.")
            (tab1,) = st.tabs(["💬 Chat"])

        else:
            st.write(f"You have access to documents and features related to the `{role}` role.")
            st.markdown("You also have access to **General documents** (e.g., company policies, holidays, announcements)")
            (tab1,) = st.tabs(["💬 Chat"])
    
 
    # --- Chat Tab ---
    with tab1:
        st.subheader("Ask a question:")
        question = st.text_input("Your Question")
        if st.button("Submit"):
            res = requests.post(
                f"{API_URL}/chat",
                json={"question": question, "role": st.session_state.role},
                auth=HTTPBasicAuth(*st.session_state.auth)
            )
            st.markdown("**Answer:**")
            if res.status_code == 200:
                st.success("✅ Answer:")
                st.write(res.json()["answer"])
            else:
                st.error("❌ Something went wrong while processing your question.")
            

    # --- Upload Tab (C-Level) ---
    if st.session_state.role == "C-Level":
        with tab2:
            st.subheader("Upload Documents")
            role_res = requests.get(f"{API_URL}/roles", auth=HTTPBasicAuth(*st.session_state.auth))
            #roles = role_res.json().get("roles", [])
            roles = st.session_state.roles

            selected_role = st.selectbox("Select document access role", roles)
            doc_file = st.file_uploader("Upload document (.md or .csv)", type=["csv", "md"])

            
            if st.button("Upload Document") and doc_file:
                res = requests.post(
                    f"{API_URL}/upload-docs",
                    files={"file": doc_file},
                    data={"role": selected_role},
                    auth=HTTPBasicAuth(*st.session_state.auth)
                )
                
                if res.ok:
                    st.success(res.json()["message"])
                else:
                    st.error(res.json().get("detail", "Something went wrong."))

        # --- Admin Tab (C-Level) ---
        with tab3:
            st.subheader("Add User")
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            new_role = st.selectbox("Assign Role", roles)
            if st.button("Create User"):
                res = requests.post(
                    f"{API_URL}/create-user",
                    data={"username": new_user, "password": new_pass, "role": new_role},
                    auth=HTTPBasicAuth(*st.session_state.auth)
                )
                
                if res.ok:
                    st.success(res.json()["message"])
                else:
                    st.error(res.json().get("detail", "Something went wrong."))

            st.subheader("Create New Role")
            new_role_input = st.text_input("New Role Name")
            if st.button("Add Role"):
                res = requests.post(
                f"{API_URL}/create-role",
                data={"role_name": new_role_input},
                auth=HTTPBasicAuth(*st.session_state.auth)
            )
                if res.ok:
                    st.success(res.json()["message"])
                    st.session_state.roles = fetch_roles()  # Refresh role list
                    st.rerun()  # Rerun so dropdowns get updated
                else:
                    st.error(res.json().get("detail", "Something went wrong."))

   
