import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import hashlib

# --- PAGE SETUP ---
# This MUST be the first Streamlit command
st.set_page_config(page_title="Indian Calorie Tracker", page_icon="🍛", layout="centered")
st.error("🚨 THIS IS THE NEW VERSION 🚨")

# --- AUTHENTICATION FUNCTIONS ---
USER_DB = "users_db.json"

def hash_password(password):
    """Scrambles the password for basic security"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as f:
            return json.load(f)
    return {}

def save_users(users_dict):
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
                    "age": new_age,
                    "weight": new_weight,
                    "height": new_height,
                    "goal_weight": new_goal,
                    "calorie_goal": 2000 # Default starting goal
                }
                save_users(users)
                st.success("Account created! You can now log in.")

# ==========================================
#               MAIN APP
# ==========================================
# Notice the indent! Everything below only runs if the user is logged in.
else:
    # --- 1. FULL FOOD DATABASE ---
    @st.cache_data
    def load_data():
        try:
            df = pd.read_csv('indian_food_db.csv')
            df.columns = df.columns.str.strip()
            if 'Dish' not in df.columns:
                dish_col = [col for col in df.columns if any(keyword in col.lower() for keyword in ['dish', 'food', 'name', 'item'])]
                df.rename(columns={dish_col[0] if dish_col else df.columns[0]: 'Dish'}, inplace=True)
            if 'Calories_per_100g' not in df.columns:
                cal_col = [col for col in df.columns if 'calorie' in col.lower() or 'kcal' in col.lower()]
                if cal_col:
                    df.rename(columns={cal_col[0]: 'Calories_per_100g'}, inplace=True)
            df['Calories_per_100g'] = df['Calories_per_100g'].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df['Calories_per_100g'] = pd.to_numeric(df['Calories_per_100g'], errors='coerce').fillna(0)
            return df, True
        except Exception as e:
            fallback_data = {
                "Dish": ["Plain Idli", "Plain Dosa", "Chicken Biryani", "Dal Tadka", "Paneer Butter Masala", "Roti/Phulka"],
                "Calories_per_100g": [130, 168, 180, 125, 350, 297]
            }
            return pd.DataFrame(fallback_data), False

    df, using_csv = load_data()

    # --- 2. PERMANENT MEMORY (User Specific!) ---
    # We name the file based on whoever is logged in so data doesn't mix!
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
        # Update the user database with their new calorie goal
        users = load_users()
        users[st.session_state.username]['calorie_goal'] = st.session_state.goal_input
        save_users(users)
        # Update the live session
        st.session_state.user_profile['calorie_goal'] = st.session_state.goal_input

    # Initialize Log
    if 'food_log' not in st.session_state:
        st.session_state.food_log = load_daily_log()
    if 'total_calories' not in st.session_state:
        st.session_state.total_calories = sum([item['Calories (kcal)'] for item in st.session_state.food_log])

    # --- TOP BAR: LOGOUT ---
    colA, colB = st.columns([4, 1])
    with colA:
        st.title(f"Welcome, {st.session_state.username}! 👋")
    with colB:
        st.write("")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear() # Wipes memory clean
            st.rerun()

    # --- 3. SIDEBAR: PROFILE & GOAL SETTING ---
    with st.sidebar:
        st.header("👤 Profile")
        st.write(f"**Weight:** {st.session_state.user_profile['weight']} kg")
        st.write(f"**Goal:** {st.session_state.user_profile['goal_weight']} kg")
        st.divider()
        st.header("🎯 Daily Goal")
        st.number_input(
            "Set Calorie Goal", 
            min_value=1000, max_value=5000, 
            value=st.session_state.user_profile['calorie_goal'], 
            step=100,
            key="goal_input",
            on_change=save_calorie_goal
        )

    current_goal = st.session_state.goal_input

    # --- 4. CIRCULAR PROGRESS METER (PLOTLY) ---
    st.subheader("📊 Today's Progress")

    if st.session_state.total_calories > current_goal:
        bar_color = "#FF4B4B" 
    elif st.session_state.total_calories > (current_goal * 0.8):
        bar_color = "#FFAA00" 
    else:
        bar_color = "#00CC96" 

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = st.session_state.total_calories,
        number = {'suffix': " kcal", 'font': {'size': 45}},
        title = {'text': f"Goal: {current_goal} kcal", 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [0, current_goal], 'tickwidth': 1},
            'bar': {'color': bar_color},
            'bgcolor': "rgba(0,0,0,0.1)",
            'borderwidth': 0,
        }
    ))

    fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- 5. FOOD LOGGER ---
    st.subheader("🍽️ Log a Meal")
    col1, col2 = st.columns([2, 1])

    with col1:
        selected_dish = st.selectbox("Search for a dish:", df['Dish'].sort_values())
    with col2:
        grams_eaten = st.number_input("Amount (grams):", min_value=10, max_value=2000, value=100, step=10)

    if st.button("➕ Log Food", type="primary", use_container_width=True):
        dish_stats = df[df['Dish'] == selected_dish].iloc[0]
        calories_added = (dish_stats['Calories_per_100g'] / 100.0) * grams_eaten
        
        st.session_state.food_log.append({
            "Dish": selected_dish,
            "Amount (g)": grams_eaten,
            "Calories (kcal)": calories_added
        })
        st.session_state.total_calories += calories_added
        save_daily_log(st.session_state.food_log)
        st.toast(f"🔥 Added {grams_eaten}g of {selected_dish}! (+{int(calories_added)} kcal)", icon="🔥")
        st.rerun()

    # --- 6. LOG HISTORY & RESET ---
    st.divider()
    st.subheader("📝 Today's Log")

    if len(st.session_state.food_log) > 0:
        log_df = pd.DataFrame(st.session_state.food_log)
        log_df['Calories (kcal)'] = log_df['Calories (kcal)'].apply(lambda x: round(x))
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        
        if st.button("🔄 Reset Entire Day", use_container_width=True):
            st.session_state.food_log = []
            st.session_state.total_calories = 0.0
            save_daily_log(st.session_state.food_log)
            st.rerun()
    else:
        st.info("No food logged yet today. Time to eat!")
