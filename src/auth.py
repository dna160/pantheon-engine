import hashlib
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

# Load env variables for Supabase connection
load_dotenv('pantheon.env', override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # Use streamlit error if running within streamlit (which require_auth will)
    if st._is_running_with_streamlit:
        st.error("Missing Supabase configuration in pantheon.env")
        st.stop()
    else:
        print("Missing Supabase configuration in pantheon.env")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def hash_password(password: str, salt: bytes = None) -> str:
    """Hashes a password using PBKDF2 HMAC SHA256 and salt."""
    if salt is None:
        salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + pwd_hash.hex()

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against the stored hash."""
    try:
        salt_hex, pwd_hash_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(pwd_hash_hex)
        actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return actual_hash == expected_hash
    except ValueError:
        return False

def get_user(username: str):
    """Fetches a user from the Supabase 'users' table by username."""
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        print(f"Error fetching user: {e}")
    return None

def deduct_credit(user_id: str, credit_type: str, amount: int = 1) -> bool:
    """
    Deducts credits for a user.
    credit_type must be either 'pantheon_credits' or 'whisperer_credits'.
    Returns True if successful, False if insufficient credits.
    """
    res = supabase.table("users").select(credit_type).eq("id", user_id).execute()
    if not res.data:
        return False
    current = res.data[0].get(credit_type, 0)
    if current < amount:
        return False
    
    update_res = supabase.table("users").update({credit_type: current - amount}).eq("id", user_id).execute()
    return bool(update_res.data)

def require_auth(app_name: str, require_superadmin: bool = False):
    """
    Streamlit UI wrapper that requires the user to log in.
    Returns the user dictionary if authenticated. If not, renders a login screen and halts execution.
    """
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is not None:
        # Check superadmin requirement if specified
        if require_superadmin and st.session_state.user.get("role") != "superadmin":
            st.error("Superadmin access required to view this dashboard.")
            if st.button("Logout"):
                st.session_state.user = None
                st.rerun()
            st.stop()
        
        # Optionally refresh user data to have current credits
        refreshed = get_user(st.session_state.user["username"])
        if refreshed:
            st.session_state.user = refreshed
        return st.session_state.user

    # Hide sidebar while logging in for a cleaner look
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 🔐 Login to {app_name}")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            with st.spinner("Authenticating..."):
                user_data = get_user(username)
                if user_data and verify_password(password, user_data["password_hash"]):
                    st.session_state.user = user_data
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    st.stop()
