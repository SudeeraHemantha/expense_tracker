"""
Streamlit Interactive Dashboard for Expense Tracker API with Persistent Cookie Auth & Security Manager.
Connects to FastAPI backend at http://127.0.0.1:8000.
"""

from datetime import date, datetime
import requests
import streamlit as st
import plotly.express as px
import pandas as pd
import extra_streamlit_components as stx

# Page Configuration
st.set_page_config(
    page_title="Expense Tracker AI",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"

# Custom CSS Theme
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #64748B;
        font-weight: 500;
    }
    .badge-ok {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-warning {
        background-color: #FEF9C3;
        color: #854D0E;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-exceeded {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Cookie Manager for Persistent Auth ---
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


# --- Session State Initializer ---
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "api_key_display" not in st.session_state:
    st.session_state["api_key_display"] = None


# --- Auto-Login Silent Refresh via Cookie ---
if not st.session_state["token"]:
    cookie_rf = cookie_manager.get(cookie="refresh_token")
    if cookie_rf:
        try:
            rf_res = requests.post(f"{API_BASE_URL}/api/auth/refresh", json={"refresh_token": cookie_rf}, timeout=3)
            if rf_res.status_code == 200:
                t_data = rf_res.json()
                st.session_state["token"] = t_data["access_token"]
                cookie_manager.set("refresh_token", t_data["refresh_token"], key="cookie_silent_refresh")

                me_res = requests.get(f"{API_BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {t_data['access_token']}"})
                if me_res.status_code == 200:
                    st.session_state["user"] = me_res.json()
                st.rerun()
        except Exception:
            pass


# --- Helper Functions ---
def get_auth_headers() -> dict:
    """Return Bearer Authorization header if token exists in session state."""
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def check_api_health() -> bool:
    """Ping FastAPI backend health endpoint."""
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return res.status_code == 200
    except Exception:
        return False


def fetch_categories() -> list:
    """Fetch registered categories for the current authenticated user."""
    try:
        res = requests.get(f"{API_BASE_URL}/api/categories", headers=get_auth_headers(), timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []


# ==========================================
# AUTHENTICATION SCREEN (IF NOT LOGGED IN)
# ==========================================
if not st.session_state["token"]:
    st.markdown('<div class="main-header">Expense Tracker & Analytics Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Please log in or register a new account to access your personal dashboard.</div>', unsafe_allow_html=True)

    auth_tab_login, auth_tab_reg = st.tabs(["🔑 Log In to Account", "📝 Register New User"])

    with auth_tab_login:
        col_l1, col_l2 = st.columns([1, 1])
        with col_l1:
            with st.form("login_form"):
                st.subheader("Login to your Dashboard")
                login_email = st.text_input("Email Address", placeholder="user@example.com")
                login_password = st.text_input("Password", type="password", placeholder="••••••••")
                submit_login = st.form_submit_button("Sign In", use_container_width=True, type="primary")

                if submit_login:
                    if not login_email.strip() or not login_password.strip():
                        st.error("Please provide both email and password.")
                    else:
                        try:
                            res = requests.post(f"{API_BASE_URL}/api/auth/login", json={"email": login_email, "password": login_password})
                            if res.status_code == 200:
                                token_data = res.json()
                                token = token_data["access_token"]
                                refresh_token = token_data.get("refresh_token")

                                st.session_state["token"] = token
                                if refresh_token:
                                    cookie_manager.set("refresh_token", refresh_token, key="cookie_set_login")

                                # Fetch User Profile
                                me_res = requests.get(f"{API_BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
                                if me_res.status_code == 200:
                                    st.session_state["user"] = me_res.json()

                                st.toast("Logged in successfully!", icon="🔑")
                                st.rerun()
                            elif res.status_code == 429:
                                st.error("Too many login attempts. Please wait a minute before trying again.")
                            else:
                                st.error("Invalid email address or password.")
                        except Exception as e:
                            st.error(f"Could not connect to API server: {e}")

    with auth_tab_reg:
        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            with st.form("register_form"):
                st.subheader("Create a New Account")
                reg_name = st.text_input("Full Name", placeholder="John Doe")
                reg_email = st.text_input("Email Address", placeholder="john@example.com")
                reg_password = st.text_input("Password", type="password", placeholder="At least 6 characters")
                submit_reg = st.form_submit_button("Create Account", use_container_width=True)

                if submit_reg:
                    if not reg_name.strip() or not reg_email.strip() or not reg_password.strip():
                        st.error("All fields are required.")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        try:
                            reg_res = requests.post(f"{API_BASE_URL}/api/auth/register", json={"full_name": reg_name, "email": reg_email, "password": reg_password})
                            if reg_res.status_code == 201:
                                st.success("Account created successfully! Please switch to the 'Log In' tab to sign in.")
                            else:
                                st.error(f"Error: {reg_res.json().get('detail', 'Registration failed')}")
                        except Exception as e:
                            st.error(f"Failed to connect to API server: {e}")

    st.stop()


# ==========================================
# AUTHENTICATED DASHBOARD SCREEN
# ==========================================
user_profile = st.session_state.get("user") or {}

# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/wallet.png", width=70)
    st.title("Expense Tracker")

    # Authenticated User Badge
    st.markdown(f"**👤 {user_profile.get('full_name', 'Authenticated User')}**")
    st.caption(f"📧 {user_profile.get('email', '')}")

    if st.button("🚪 Log Out", use_container_width=True):
        cookie_manager.delete("refresh_token", key="cookie_del_logout")
        st.session_state["token"] = None
        st.session_state["user"] = None
        st.session_state["api_key_display"] = None
        st.rerun()

    st.divider()

    # API Connection Badge
    is_online = check_api_health()
    if is_online:
        st.success("🟢 API Server Connected")
    else:
        st.error("🔴 API Server Offline (http://127.0.0.1:8000)")

    st.divider()

    categories_list = fetch_categories()
    category_options = {c["name"]: c["id"] for c in categories_list} if categories_list else {}

    # Manual Expense Logger Form
    with st.expander("➕ Log Expense Manually", expanded=False):
        with st.form("manual_expense_form"):
            amount = st.number_input("Amount", min_value=0.01, step=10.0, value=100.0)
            currency = st.selectbox("Currency", ["LKR", "USD", "EUR", "GBP", "INR"])
            description = st.text_input("Description", placeholder="e.g. Lunch at restaurant")

            selected_cat_name = st.selectbox(
                "Category",
                options=list(category_options.keys()) if category_options else ["No categories"]
            )
            expense_date = st.date_input("Date", value=date.today())
            notes = st.text_area("Notes (Optional)", placeholder="Additional details...")

            submit_manual = st.form_submit_button("Submit Transaction", use_container_width=True)

            if submit_manual:
                if not category_options:
                    st.error("Please add a category first.")
                elif not description.strip():
                    st.error("Description is required.")
                else:
                    payload = {
                        "amount": amount,
                        "currency": currency,
                        "description": description,
                        "category_id": category_options[selected_cat_name],
                        "expense_date": expense_date.isoformat(),
                        "notes": notes
                    }
                    try:
                        res = requests.post(f"{API_BASE_URL}/api/expenses", json=payload, headers=get_auth_headers())
                        if res.status_code == 201:
                            st.toast("Expense logged successfully!", icon="✅")
                            st.rerun()
                        else:
                            st.error(f"Error: {res.json().get('detail', 'Failed to save')}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")

    # Category Creation Form
    with st.expander("🏷️ Add New Category", expanded=False):
        with st.form("add_category_form"):
            cat_name = st.text_input("Category Name", placeholder="e.g. Travel")
            cat_desc = st.text_input("Description", placeholder="e.g. Flights and hotels")
            submit_cat = st.form_submit_button("Create Category", use_container_width=True)

            if submit_cat:
                if not cat_name.strip():
                    st.error("Category name required.")
                else:
                    try:
                        res = requests.post(f"{API_BASE_URL}/api/categories", json={"name": cat_name, "description": cat_desc}, headers=get_auth_headers())
                        if res.status_code == 201:
                            st.toast(f"Category '{cat_name}' created!", icon="🎉")
                            st.rerun()
                        else:
                            st.error(f"Error: {res.json().get('detail', 'Failed')}")
                    except Exception as e:
                        st.error(f"Failed: {e}")

    # Budget Limits Form
    with st.expander("🎯 Set Monthly Budget", expanded=False):
        with st.form("set_budget_form"):
            b_cat_name = st.selectbox("Category", options=list(category_options.keys()) if category_options else ["No categories"], key="b_cat")
            b_limit = st.number_input("Monthly Limit", min_value=1.0, step=500.0, value=10000.0)
            b_month = st.number_input("Month (1-12)", min_value=1, max_value=12, value=date.today().month)
            b_year = st.number_input("Year (YYYY)", min_value=2000, max_value=2100, value=date.today().year)
            submit_budget = st.form_submit_button("Save Budget Limit", use_container_width=True)

            if submit_budget:
                if not category_options:
                    st.error("Create a category first.")
                else:
                    payload = {
                        "category_id": category_options[b_cat_name],
                        "monthly_limit": b_limit,
                        "month": int(b_month),
                        "year": int(b_year)
                    }
                    try:
                        res = requests.post(f"{API_BASE_URL}/api/analytics/budgets", json=payload, headers=get_auth_headers())
                        if res.status_code == 201:
                            st.toast("Budget threshold set successfully!", icon="🎯")
                            st.rerun()
                        else:
                            st.error(f"Error: {res.json().get('detail', 'Failed')}")
                    except Exception as e:
                        st.error(f"Request error: {e}")


# --- Main Application Header ---
st.markdown('<div class="main-header">Expense Tracker & Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Multi-User Financial Dashboard & Automation Engine</div>', unsafe_allow_html=True)

# Main Navigation Tabs
tab_ai, tab_vision, tab_recurring, tab_analytics, tab_budgets, tab_export_import, tab_history, tab_settings = st.tabs([
    "🤖 AI Text Parsing",
    "📸 Scan Receipt (OCR)",
    "🔁 Subscriptions",
    "📊 Monthly Analytics",
    "🔔 Budget Alerts",
    "📤 Export & Import",
    "📋 Transaction History",
    "⚙️ Settings & Security"
])


# ==========================================
# TAB 1: AI Natural Language Ingestion
# ==========================================
with tab_ai:
    st.subheader("🤖 Natural Language Expense Ingestion")
    st.write("Type any freeform sentence to extract and log your expense automatically.")

    example_col1, example_col2, example_col3 = st.columns(3)
    with example_col1:
        if st.button("💡 Example 1: Groceries yesterday", use_container_width=True):
            st.session_state["ai_text_input"] = "Spent 3500 LKR on groceries and vegetables yesterday"
    with example_col2:
        if st.button("💡 Example 2: Fuel today", use_container_width=True):
            st.session_state["ai_text_input"] = "Paid 2500 LKR for petrol fuel fill up today"
    with example_col3:
        if st.button("💡 Example 3: Utility Bill", use_container_width=True):
            st.session_state["ai_text_input"] = "Paid 8500 LKR for electricity bill payment last Friday"

    user_text = st.text_input(
        "Enter expense description:",
        key="ai_text_input",
        placeholder="e.g. 'Spent 4200 LKR on supermarket groceries yesterday'"
    )

    if st.button("⚡ Parse & Log Expense Transaction", type="primary", use_container_width=True):
        if not user_text.strip():
            st.warning("Please enter a sentence describing your expense.")
        else:
            with st.spinner("AI parsing amount, currency, relative date, and category..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/api/ai/parse-expense", json={"text": user_text}, headers=get_auth_headers())
                    if res.status_code == 201:
                        data = res.json()
                        st.balloons()
                        st.success("Transaction Successfully Parsed and Saved to Database!")

                        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
                        with res_col1:
                            st.metric("Amount", f"{data['currency']} {data['amount']:,.2f}")
                        with res_col2:
                            st.metric("Category", data["category"]["name"])
                        with res_col3:
                            st.metric("Expense Date", data["expense_date"])
                        with res_col4:
                            st.metric("Description", data["description"])

                        st.caption(f"📌 Notes: {data.get('notes', '')}")
                    else:
                        st.error(f"Parsing Error: {res.json().get('detail', 'Could not parse text')}")
                except Exception as e:
                    st.error(f"Failed to connect to API server: {e}")


# ==========================================
# TAB 2: AI Vision Receipt OCR Scanning
# ==========================================
with tab_vision:
    st.subheader("📸 Scan Receipt Image (OCR)")
    st.write("Upload or capture a photo of a receipt to automatically extract store, total, date, and line items.")

    input_mode = st.radio("Choose Image Input Method:", ["📁 Upload Receipt Image File", "📷 Live Camera Capture"], horizontal=True)

    uploaded_file = None
    if input_mode == "📁 Upload Receipt Image File":
        uploaded_file = st.file_uploader(
            "Upload Receipt Photo (JPEG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"],
            help="Upload a clear photo of your store or restaurant receipt."
        )
    else:
        uploaded_file = st.camera_input("Take a photo of your receipt")

    if uploaded_file is not None:
        img_bytes = uploaded_file.getvalue()

        col_img, col_proc = st.columns([1, 1])
        with col_img:
            st.image(img_bytes, caption="Uploaded Receipt Preview", use_container_width=True)

        with col_proc:
            st.info("Receipt Image Loaded Ready for OCR Vision Analysis.")

            if st.button("🚀 Process & Log Receipt Image", type="primary", use_container_width=True):
                with st.spinner("AI Vision scanning receipt image for merchant, date, total, and line items..."):
                    try:
                        mime = uploaded_file.type or "image/jpeg"
                        files = {"file": (uploaded_file.name or "receipt.jpg", img_bytes, mime)}
                        res = requests.post(f"{API_BASE_URL}/api/ai/parse-receipt", files=files, headers=get_auth_headers())

                        if res.status_code == 201:
                            res_data = res.json()
                            parsed = res_data["parsed_receipt"]
                            exp_obj = res_data["expense"]

                            st.balloons()
                            st.success("Receipt Successfully Scanned and Logged to Database!")

                            r1, r2, r3, r4 = st.columns(4)
                            with r1:
                                st.metric("Merchant / Store", parsed.get("merchant_name") or "Store Purchase")
                            with r2:
                                st.metric("Total Amount", f"{parsed['currency']} {parsed['total_amount']:,.2f}")
                            with r3:
                                st.metric("Category", parsed["category_name"])
                            with r4:
                                st.metric("Receipt Date", parsed["receipt_date"])

                            if parsed.get("line_items"):
                                st.write("#### 🛒 Extracted Line Items")
                                df_items = pd.DataFrame(parsed["line_items"])
                                df_items = df_items.rename(columns={"item_name": "Item Description", "amount": "Item Amount (LKR)"})
                                st.dataframe(df_items, use_container_width=True)
                        else:
                            st.error(f"Receipt Processing Failed: {res.json().get('detail', 'Could not process image')}")
                    except Exception as e:
                        st.error(f"Error calling API server: {e}")


# ==========================================
# TAB 3: Subscriptions & Recurring Expenses
# ==========================================
with tab_recurring:
    st.subheader("🔁 Subscriptions & Recurring Expense Commitments")
    st.write("Manage recurring monthly bills, subscriptions, and automatic transaction logging.")

    rec_top_col1, rec_top_col2 = st.columns([3, 1])
    with rec_top_col2:
        if st.button("⚡ Process Due Subscriptions Now", type="primary", use_container_width=True):
            try:
                p_res = requests.post(f"{API_BASE_URL}/api/recurring/process", headers=get_auth_headers())
                if p_res.status_code == 200:
                    logged = p_res.json()
                    st.toast(f"Processed {len(logged)} due subscription(s)!", icon="⚡")
                    st.rerun()
                else:
                    st.error("Failed to process due subscriptions.")
            except Exception as e:
                st.error(f"Error connecting to server: {e}")

    try:
        rec_res = requests.get(f"{API_BASE_URL}/api/recurring", headers=get_auth_headers())
        if rec_res.status_code == 200:
            subscriptions = rec_res.json()

            active_count = len(subscriptions)
            due_today_count = sum(1 for s in subscriptions if s["next_due_date"] <= date.today().isoformat())
            total_monthly_committed = 0.0

            for s in subscriptions:
                amt = s["amount"]
                freq = s["frequency"].upper()
                if freq == "MONTHLY":
                    total_monthly_committed += amt
                elif freq == "WEEKLY":
                    total_monthly_committed += amt * 4.33
                elif freq == "DAILY":
                    total_monthly_committed += amt * 30.0
                elif freq == "YEARLY":
                    total_monthly_committed += amt / 12.0

            rm1, rm2, rm3 = st.columns(3)
            with rm1:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">LKR {total_monthly_committed:,.2f}</div>
                    <div class="metric-label">Committed Monthly Subscriptions</div>
                </div>
                ''', unsafe_allow_html=True)
            with rm2:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">{active_count}</div>
                    <div class="metric-label">Active Subscriptions</div>
                </div>
                ''', unsafe_allow_html=True)
            with rm3:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">{due_today_count}</div>
                    <div class="metric-label">Due / Overdue Items</div>
                </div>
                ''', unsafe_allow_html=True)

            st.divider()

            with st.expander("➕ Register New Subscription / Recurring Bill", expanded=False):
                with st.form("new_recurring_form"):
                    rc_col1, rc_col2 = st.columns(2)
                    with rc_col1:
                        rec_title = st.text_input("Subscription Title", placeholder="e.g. Netflix Premium, Fiber Internet")
                        rec_amount = st.number_input("Amount", min_value=1.0, step=50.0, value=1500.0)
                        rec_currency = st.selectbox("Currency", ["LKR", "USD", "EUR", "GBP"], key="rec_curr")
                    with rc_col2:
                        rec_cat_name = st.selectbox("Category", options=list(category_options.keys()) if category_options else ["No categories"], key="rec_cat")
                        rec_freq = st.selectbox("Frequency", ["MONTHLY", "WEEKLY", "DAILY", "YEARLY"], index=0)
                        rec_start = st.date_input("Start Date", value=date.today())

                    rec_autolog = st.checkbox("Auto-log expense when due date arrives", value=True)
                    submit_rec = st.form_submit_button("Save Subscription Commitment", use_container_width=True)

                    if submit_rec:
                        if not category_options:
                            st.error("Add a category first.")
                        elif not rec_title.strip():
                            st.error("Title is required.")
                        else:
                            rec_payload = {
                                "title": rec_title,
                                "amount": rec_amount,
                                "currency": rec_currency,
                                "category_id": category_options[rec_cat_name],
                                "frequency": rec_freq,
                                "start_date": rec_start.isoformat(),
                                "auto_log": rec_autolog
                            }
                            try:
                                create_res = requests.post(f"{API_BASE_URL}/api/recurring", json=rec_payload, headers=get_auth_headers())
                                if create_res.status_code == 201:
                                    st.toast(f"Subscription '{rec_title}' registered!", icon="🔁")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {create_res.json().get('detail', 'Failed')}")
                            except Exception as e:
                                st.error(f"Request failed: {e}")

            st.write("#### Active Subscription Commitments")
            if subscriptions:
                df_rec = pd.DataFrame(subscriptions)
                df_rec["category_name"] = df_rec["category"].apply(lambda x: x["name"] if isinstance(x, dict) and "name" in x else "N/A")

                disp_rec = df_rec[["id", "title", "amount", "currency", "frequency", "category_name", "next_due_date", "auto_log"]]
                disp_rec.columns = ["ID", "Title", "Amount", "Currency", "Frequency", "Category", "Next Due Date", "Auto Log"]

                st.dataframe(disp_rec, use_container_width=True)

                with st.expander("🗑️ Delete Recurring Subscription Rule", expanded=False):
                    del_rec_id = st.number_input("Enter Recurring ID to delete", min_value=1, step=1, key="del_rec")
                    if st.button("Delete Recurring Rule", type="secondary"):
                        d_res = requests.delete(f"{API_BASE_URL}/api/recurring/{del_rec_id}", headers=get_auth_headers())
                        if d_res.status_code == 204:
                            st.toast(f"Subscription ID #{del_rec_id} deleted!", icon="🗑️")
                            st.rerun()
                        else:
                            st.error("Subscription rule not found.")
            else:
                st.info("No active recurring subscriptions registered.")
    except Exception as e:
        st.error(f"Error fetching recurring subscriptions: {e}")


# ==========================================
# TAB 4: Monthly Analytics & Visual Reports
# ==========================================
with tab_analytics:
    st.subheader("📊 Monthly Financial Spending Breakdown")

    ctrl_col1, ctrl_col2, _ = st.columns([1, 1, 2])
    with ctrl_col1:
        sel_year = st.selectbox("Year", options=[2026, 2025, 2024], index=0)
    with ctrl_col2:
        sel_month = st.selectbox("Month", options=list(range(1, 13)), index=date.today().month - 1)

    try:
        res = requests.get(f"{API_BASE_URL}/api/analytics/monthly?year={sel_year}&month={sel_month}", headers=get_auth_headers())
        if res.status_code == 200:
            report = res.json()
            total_spent = report["total_spent"]
            breakdown = report["breakdown_by_category"]

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">LKR {total_spent:,.2f}</div>
                    <div class="metric-label">Total Monthly Spending</div>
                </div>
                ''', unsafe_allow_html=True)
            with m2:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">{len(breakdown)}</div>
                    <div class="metric-label">Active Spending Categories</div>
                </div>
                ''', unsafe_allow_html=True)
            with m3:
                top_cat = breakdown[0]["name"] if breakdown else "N/A"
                top_amt = breakdown[0]["total_spent"] if breakdown else 0.0
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-value">{top_cat}</div>
                    <div class="metric-label">Highest Expense Category (LKR {top_amt:,.2f})</div>
                </div>
                ''', unsafe_allow_html=True)

            st.divider()

            if breakdown:
                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    st.write("#### Category Share Breakdown")
                    df_chart = pd.DataFrame(breakdown)
                    fig_donut = px.pie(
                        df_chart,
                        names="name",
                        values="total_spent",
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                    fig_donut.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig_donut, use_container_width=True)

                with chart_col2:
                    st.write("#### Category Spending Amounts")
                    fig_bar = px.bar(
                        df_chart,
                        x="name",
                        y="total_spent",
                        labels={"name": "Category", "total_spent": "Amount (LKR)"},
                        color="total_spent",
                        color_continuous_scale="Viridis"
                    )
                    fig_bar.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig_bar, use_container_width=True)

                st.write("#### Category Spending Breakdown Table")
                st.dataframe(
                    df_chart.rename(columns={
                        "name": "Category Name",
                        "total_spent": "Total Spent (LKR)",
                        "percentage": "Percentage Share (%)"
                    }),
                    use_container_width=True
                )
            else:
                st.info("No expense transactions recorded for the selected month.")
        else:
            st.error("Failed to load monthly analytics report.")
    except Exception as e:
        st.error(f"Error fetching analytics data: {e}")


# ==========================================
# TAB 5: Budget Threshold Alerts
# ==========================================
with tab_budgets:
    st.subheader("🔔 Category Budget Threshold Alerts")
    st.write("Monitor category monthly spending against configured budget limits.")

    b_col1, b_col2, _ = st.columns([1, 1, 2])
    with b_col1:
        bg_year = st.selectbox("Budget Year", options=[2026, 2025, 2024], index=0, key="bg_y")
    with b_col2:
        bg_month = st.selectbox("Budget Month", options=list(range(1, 13)), index=date.today().month - 1, key="bg_m")

    try:
        res = requests.get(f"{API_BASE_URL}/api/analytics/budgets?year={bg_year}&month={bg_month}", headers=get_auth_headers())
        if res.status_code == 200:
            alerts = res.json()
            if alerts:
                for b_alert in alerts:
                    cat = b_alert["category"]
                    limit = b_alert["limit"]
                    spent = b_alert["spent"]
                    status_level = b_alert["status"]

                    pct = (spent / limit * 100.0) if limit > 0 else 0.0

                    card_col1, card_col2, card_col3 = st.columns([3, 2, 2])
                    with card_col1:
                        st.markdown(f"**{cat}**")
                        st.progress(min(pct / 100.0, 1.0))
                    with card_col2:
                        st.write(f"Spent: **LKR {spent:,.2f}** / Limit: **LKR {limit:,.2f}** ({pct:.1f}%)")
                    with card_col3:
                        if status_level == "EXCEEDED":
                            st.markdown('<span class="badge-exceeded">🚨 EXCEEDED</span>', unsafe_allow_html=True)
                        elif status_level == "WARNING":
                            st.markdown('<span class="badge-warning">⚠️ WARNING (>=80%)</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="badge-ok">✅ OK</span>', unsafe_allow_html=True)

                    st.divider()
            else:
                st.info("No budget thresholds configured for this month. Set budget limits in the sidebar.")
    except Exception as e:
        st.error(f"Error checking budgets: {e}")


# ==========================================
# TAB 6: Data Export & Bulk Bank Statement Import
# ==========================================
with tab_export_import:
    st.subheader("📤 Financial Data Export & Bulk Bank Statement CSV Import")

    ex_col, im_col = st.columns(2)

    with ex_col:
        st.write("### 📥 Export Monthly Financial Reports")
        st.write("Generate and download transaction logs for accounting or tax reporting.")

        ey_col1, ey_col2 = st.columns(2)
        with ey_col1:
            exp_year = st.selectbox("Export Year", options=[2026, 2025, 2024], index=0, key="exp_y")
        with ey_col2:
            exp_month = st.selectbox("Export Month", options=list(range(1, 13)), index=date.today().month - 1, key="exp_m")

        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            try:
                csv_res = requests.get(f"{API_BASE_URL}/api/export/csv?year={exp_year}&month={exp_month}", headers=get_auth_headers())
                if csv_res.status_code == 200:
                    st.download_button(
                        label="📄 Download CSV Report",
                        data=csv_res.content,
                        file_name=f"expenses_{exp_year}_{exp_month:02d}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            except Exception as e:
                st.error("Error fetching CSV")

        with btn_col2:
            try:
                xlsx_res = requests.get(f"{API_BASE_URL}/api/export/excel?year={exp_year}&month={exp_month}", headers=get_auth_headers())
                if xlsx_res.status_code == 200:
                    st.download_button(
                        label="📊 Download Excel Report (.xlsx)",
                        data=xlsx_res.content,
                        file_name=f"expenses_report_{exp_year}_{exp_month:02d}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error("Error fetching Excel workbook")

    with im_col:
        st.write("### 📥 Bulk Import Bank Statement CSV")
        st.write("Upload a CSV file exported from your bank or wallet. Auto-categorizes line items.")

        bank_file = st.file_uploader("Upload Bank Statement (.csv)", type=["csv"], key="bank_csv_up")
        if bank_file is not None:
            if st.button("🚀 Process & Bulk Import Statement", type="primary", use_container_width=True):
                with st.spinner("Parsing statement rows, detecting headers, and auto-categorizing transactions..."):
                    try:
                        files = {"file": (bank_file.name, bank_file.getvalue(), "text/csv")}
                        imp_res = requests.post(f"{API_BASE_URL}/api/import/csv", files=files, headers=get_auth_headers())

                        if imp_res.status_code == 200:
                            summary = imp_res.json()["summary"]
                            st.balloons()
                            st.success("Bank Statement Bulk Import Completed Successfully!")

                            ic1, ic2, ic3 = st.columns(3)
                            with ic1:
                                st.metric("Total CSV Rows", summary["total_rows"])
                            with ic2:
                                st.metric("Imported Transactions", summary["imported_count"])
                            with ic3:
                                st.metric("Skipped / Invalid", summary["skipped_count"])
                        else:
                            st.error(f"Import failed: {imp_res.json().get('detail', 'Could not parse CSV')}")
                    except Exception as e:
                        st.error(f"Error calling import endpoint: {e}")


# ==========================================
# TAB 7: Transaction History
# ==========================================
with tab_history:
    st.subheader("📋 Expense Transaction History & Management")

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        filter_cat = st.selectbox(
            "Filter by Category",
            options=["All Categories"] + list(category_options.keys()) if category_options else ["All Categories"]
        )

    try:
        cat_filter_id = category_options.get(filter_cat) if filter_cat != "All Categories" else None
        query_url = f"{API_BASE_URL}/api/expenses"
        if cat_filter_id:
            query_url += f"?category_id={cat_filter_id}"

        res = requests.get(query_url, headers=get_auth_headers())
        if res.status_code == 200:
            expenses = res.json()
            if expenses:
                df_exp = pd.DataFrame(expenses)
                df_exp["category_name"] = df_exp["category"].apply(lambda x: x["name"] if isinstance(x, dict) and "name" in x else "N/A")

                display_df = df_exp[["id", "expense_date", "description", "category_name", "amount", "currency", "notes"]]
                display_df.columns = ["ID", "Date", "Description", "Category", "Amount", "Currency", "Notes"]

                st.dataframe(display_df, use_container_width=True)

                with st.expander("🗑️ Delete Transaction", expanded=False):
                    del_id = st.number_input("Enter Expense ID to delete", min_value=1, step=1)
                    if st.button("Confirm Delete", type="secondary"):
                        del_res = requests.delete(f"{API_BASE_URL}/api/expenses/{del_id}", headers=get_auth_headers())
                        if del_res.status_code == 204:
                            st.toast(f"Expense ID {del_id} deleted!", icon="🗑️")
                            st.rerun()
                        else:
                            st.error("Expense ID not found.")
            else:
                st.info("No transaction records found.")
    except Exception as e:
        st.error(f"Error fetching transaction history: {e}")


# ==========================================
# TAB 8: Settings & Security Manager
# ==========================================
with tab_settings:
    st.subheader("⚙️ User Profile & Security Settings")
    st.write("Manage your personal profile, generate API keys for automated integrations, and control session security.")

    set_col1, set_col2 = st.columns(2)

    with set_col1:
        st.write("### 👤 Profile Details")
        st.write(f"**Full Name:** {user_profile.get('full_name', 'N/A')}")
        st.write(f"**Email Address:** {user_profile.get('email', 'N/A')}")
        st.write(f"**Account Status:** Active ✅")
        st.write(f"**User ID:** `{user_profile.get('id', 'N/A')}`")

    with set_col2:
        st.write("### 🔑 Personal API Key Manager")
        st.write("Generate a persistent, revocable API key (`sk_live_...`) to rapidly log expenses via HTTP without logging in through a browser.")

        if st.button("Generate / Regenerate Personal API Key", type="primary", use_container_width=True):
            try:
                k_res = requests.post(f"{API_BASE_URL}/api/auth/api-key", headers=get_auth_headers())
                if k_res.status_code == 200:
                    k_data = k_res.json()
                    st.session_state["api_key_display"] = k_data["api_key"]
                    st.toast("New Personal API Key generated!", icon="🔑")
                else:
                    st.error("Failed to generate API Key.")
            except Exception as e:
                st.error(f"Error calling API key endpoint: {e}")

        if st.session_state.get("api_key_display"):
            st.warning("⚠️ Make sure to copy your API key now. You won't be able to see it again!")
            st.code(st.session_state["api_key_display"], language="text")
            st.caption("Pass this key in HTTP header: `X-API-Key: sk_live_...`")

    st.divider()

    st.write("### 🔒 Session & Security Controls")
    st.write("Clear your active 30-day refresh token cookie and terminate all active browser sessions.")

    if st.button("🚪 Revoke Refresh Token & Log Out", type="secondary"):
        cookie_manager.delete("refresh_token", key="cookie_del_settings")
        st.session_state["token"] = None
        st.session_state["user"] = None
        st.session_state["api_key_display"] = None
        st.rerun()
