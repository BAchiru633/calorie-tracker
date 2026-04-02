import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import hashlib

# --- PAGE SETUP ---
# This MUST be the first Streamlit command
st.set_page_config(page_title="Indian Calorie Tracker", page_icon="🍛", layout="centered")

# --- AUTHENTICATION FUNCTIONS ---
USER_DB = "users_db.json"

def hash_password(password):
    """Scrambles the password for basic security"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Loads the user database from a JSON file"""
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as f:
            return json.load(f)
    return {}

def save_users(users_dict):
    """Saves the user database to a JSON file"""
    with open(USER_DB, "w") as f:
        json.dump(users_dict, f)

# --- INITIALIZE SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# ==========================================
#         LOGIN & SIGN UP SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.title("🍛 Indian Calorie Tracker")
    st.subheader("Please log in to continue")
    
    # Create tabs for Login and Sign Up
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    
    with tab_login:
        st.write("Welcome back!")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", type="primary"):
            users = load_users()
            if login_user in users:
                if users[login_user]['password'] == hash_password(login_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.session_state.user_profile = users[login_user]
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("Username not found.")
                
    with tab_signup:
        st.write("Create a new profile!")
        new_user = st.text_input("Choose a Username", key="new_user")
        new_pass = st.text_input("Choose a Password", type="password", key="new_pass")
        
        # Gender is required for accurate BMR and Body Fat calculations
        new_gender = st.radio("Gender", ["Male", "Female"], horizontal=True)
        
        col1, col2 = st.columns(2)
        with col1:
            new_age = st.number_input("Age", min_value=10, max_value=120, value=25)
            new_weight = st.number_input("Current Weight (kg)", min_value=30.0, max_value=300.0, value=70.0)
        with col2:
            new_height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0)
            new_goal = st.number_input("Goal Weight (kg)", min_value=30.0, max_value=300.0, value=65.0)
            
        if st.button("Sign Up", type="primary"):
            users = load_users()
            if new_user in users:
                st.error("Username already exists! Please choose another.")
            elif not new_user or not new_pass:
                st.warning("Please fill out both username and password.")
            else:
                # Save the new user to our JSON database
                users[new_user] = {
                    "password": hash_password(new_pass),
                    "gender": new_gender,
                    "age": new_age,
                    "weight": new_weight,
                    "height": new_height,
                    "goal_weight": new_goal,
                    "calorie_goal": 2000 # Default starting goal
                }
                save_users(users)
                st.success("Account created! You can now log in from the Login tab.")

# ==========================================
#               MAIN APP DASHBOARD
# ==========================================
else:
    # --- 1. FULL FOOD DATABASE ---
    @st.cache_data
    def load_data():
        try:
            df = pd.read_csv('indian_food_db.csv')
            df.columns = df.columns.str.strip()
            # Standardize 'Dish' column
            if 'Dish' not in df.columns:
                dish_col = [col for col in df.columns if any(keyword in col.lower() for keyword in ['dish', 'food', 'name', 'item'])]
                df.rename(columns={dish_col[0] if dish_col else df.columns[0]: 'Dish'}, inplace=True)
            # Standardize 'Calories' column
            if 'Calories_per_100g' not in df.columns:
                cal_col = [col for col in df.columns if 'calorie' in col.lower() or 'kcal' in col.lower()]
                if cal_col:
                    df.rename(columns={cal_col[0]: 'Calories_per_100g'}, inplace=True)
            # Clean calories column to strictly numeric
            df['Calories_per_100g'] = df['Calories_per_100g'].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df['Calories_per_100g'] = pd.to_numeric(df['Calories_per_100g'], errors='coerce').fillna(0)
            return df, True
        except Exception as e:
            # Fallback data if CSV fails
            fallback_data = {
                "Dish": ["Plain Idli", "Plain Dosa", "Chicken Biryani", "Dal Tadka", "Paneer Butter Masala", "Roti/Phulka"],
                "Calories_per_100g": [130, 168, 180, 125, 350, 297]
            }
            return pd.DataFrame(fallback_data), False

    df, using_csv = load_data()

    # --- 2. PERMANENT MEMORY (User Specific) ---
    LOG_FILE = f"{st.session_state.username}_log.csv"

    def load_daily_log():
        if os.path.exists(LOG_FILE):
            return pd.read_csv(LOG_FILE).to_dict('records')
        return []

    def save_daily_log(log_list):
        if len(log_list) > 0:
            pd.DataFrame(log_list).to_csv(LOG_FILE, index=False)
        else:
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                
    def save_calorie_goal():
        users = load_users()
        users[st.session_state.username]['calorie_goal'] = st.session_state.goal_input
        save_users(users)
        st.session_state.user_profile['calorie_goal'] = st.session_state.goal_input

    # Initialize user's personal log
    if 'food_log' not in st.session_state:
        st.session_state.food_log = load_daily_log()
    if 'total_calories' not in st.session_state:
        st.session_state.total_calories = sum([item['Calories (kcal)'] for item in st.session_state.food_log])

    # --- TOP BAR: WELCOME & LOGOUT ---
    colA, colB = st.columns([4, 1])
    with colA:
        st.title(f"Welcome, {st.session
