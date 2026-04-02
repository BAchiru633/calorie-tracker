import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import hashlib
import datetime
import extra_streamlit_components as stx
from streamlit_gsheets import GSheetsConnection

# --- PAGE SETUP ---
st.set_page_config(page_title="Indian Calorie Tracker", page_icon="🍛", layout="centered")

# ==========================================
#         DATABASE CONNECTION (GOOGLE SHEETS)
# ==========================================
# PASTE YOUR GOOGLE SHEET URL HERE:
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1gqjP15Pz1GUy_7005_qswSfpjFh41LZFlsDNXu9AYuQ/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# Initialize Cookie Manager for Persistent Logins
cookie_manager = stx.CookieManager()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    try:
        df = conn.read(worksheet="Users", spreadsheet=SPREADSHEET_URL, ttl=0)
        df = df.dropna(how="all") 
        if df.empty or 'username' not in df.columns: 
            return {}
        df = df.dropna(subset=['username'])
        return df.set_index('username').to_dict('index')
    except Exception as e:
        return {}

def save_users(users_dict):
    df = pd.DataFrame.from_dict(users_dict, orient='index').reset_index()
    df.rename(columns={'index': 'username'}, inplace=True)
    conn.update(worksheet="Users", data=df, spreadsheet=SPREADSHEET_URL)

def load_daily_log(username):
    try:
        df = conn.read(worksheet="Logs", spreadsheet=SPREADSHEET_URL, ttl=0).dropna(how="all")
        if df.empty or 'username' not in df.columns: 
            return []
        user_logs = df[df['username'] == username].drop(columns=['username']).to_dict('records')
        return user_logs
    except:
        return []

def save_daily_log(username, user_log_list):
    try:
        all_logs_df = conn.read(worksheet="Logs", spreadsheet=SPREADSHEET_URL, ttl=0).dropna(how="all")
        if not all_logs_df.empty and 'username' in all_logs_df.columns:
            all_logs_df = all_logs_df[all_logs_df['username'] != username]
        else:
            all_logs_df = pd.DataFrame(columns=['username', 'Dish', 'Amount (g)', 'Calories (kcal)'])
    except:
        all_logs_df = pd.DataFrame(columns=['username', 'Dish', 'Amount (g)', 'Calories (kcal)'])

    if len(user_log_list) > 0:
        new_logs_df = pd.DataFrame(user_log_list)
        new_logs_df['username'] = username 
        all_logs_df = pd.concat([all_logs_df, new_logs_df], ignore_index=True)

    conn.update(worksheet="Logs", data=all_logs_df, spreadsheet=SPREADSHEET_URL)

# --- INITIALIZE SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# --- AUTO-LOGIN VIA COOKIE (30 DAY PERSISTENCE) ---
auth_cookie = cookie_manager.get(cookie="auth_token")
if auth_cookie and not st.session_state.logged_in:
    users = load_users()
    if auth_cookie in users:
        st.session_state.logged_in = True
        st.session_state.username = auth_cookie
        st.session_state.user_profile = users[auth_cookie]

# ==========================================
#         LOGIN & SIGN UP SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.title("🍛 Indian Calorie Tracker")
    st.subheader("Please log in to continue")
    
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    
    with tab_login:
        st.write("Welcome back!")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", type="primary"):
            users = load_users()
            if login_user in users:
                if str(users[login_user]['password']) == hash_password(login_pass):
                    
                    # DROP A COOKIE THAT LASTS FOR 30 DAYS!
                    cookie_manager.set("auth_token", login_user, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    
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
                users[new_user] = {
                    "password": hash_password(new_pass),
                    "gender": new_gender,
                    "age": new_age,
                    "weight": new_weight,
                    "height": new_height,
                    "goal_weight": new_goal,
                    "calorie_goal": 2000
                }
                save_users(users) 
                st.success("Account created! You can now log in from the Login tab.")

# ==========================================
#               MAIN APP DASHBOARD
# ==========================================
else:
    @st.cache_data(ttl=86400) 
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

    def save_calorie_goal():
        users = load_users()
        users[st.session_state.username]['calorie_goal'] = st.session_state.goal_input
        save_users(users)
        st.session_state.user_profile['calorie_goal'] = st.session_state.goal_input

    if 'food_log' not in st.session_state:
        st.session_state.food_log = load_daily_log(st.session_state.username)
    if 'total_calories' not in st.session_state:
        st.session_state.total_calories = sum([item['Calories (kcal)'] for item in st.session_state.food_log])

    # --- TOP BAR: WELCOME & LOGOUT ---
    colA, colB = st.columns([4, 1])
    with colA:
        st.title(f"Welcome, {st.session_state.username}! 👋")
    with colB:
        st.write("")
        if st.button("Logout", use_container_width=True):
            # SHRED THE COOKIE ON LOGOUT
            cookie_manager.delete("auth_token")
            st.session_state.clear() 
            st.rerun()

    # ==========================================
    #               SIDEBAR & TOOLS
    # ==========================================
    with st.sidebar:
        st.header("👤 Profile")
        st.write(f"**Weight:** {st.session_state.user_profile.get('weight', 'N/A')} kg")
        st.write(f"**Goal:** {st.session_state.user_profile.get('goal_weight', 'N/A')} kg")
        
        st.divider()
        st.header("🎯 Daily Goal")
        st.number_input(
            "Set Calorie Goal", 
            min_value=1000, max_value=5000, 
            value=int(st.session_state.user_profile.get('calorie_goal', 2000)), 
            step=100,
            key="goal_input",
            on_change=save_calorie_goal
        )

        st.divider()
        st.header("🧮 Health Tools")
        
        u_weight = st.session_state.user_profile.get('weight', 70)
        u_height = st.session_state.user_profile.get('height', 170)
        u_age = st.session_state.user_profile.get('age', 25)
        u_gender = st.session_state.user_profile.get('gender', 'Male') 
        
        with st.expander("⚖️ BMI Calculator"):
            bmi = u_weight / ((u_height / 100) ** 2)
            st.metric("Your BMI", f"{bmi:.1f}")
            if bmi < 18.5: st.warning("Classification: Underweight")
            elif 18.5 <= bmi < 24.9: st.success("Classification: Normal Weight")
            elif 25 <= bmi < 29.9: st.warning("Classification: Overweight")
            else: st.error("Classification: Obese")

        with st.expander("🔥 Daily Calorie Needs"):
            activity_level = st.selectbox("Activity Level", ["Sedentary", "Lightly Active", "Moderately Active", "Very Active"])
            if u_gender == "Male":
                bmr = (10 * u_weight) + (6.25 * u_height) - (5 * u_age) + 5
            else:
                bmr = (10 * u_weight) + (6.25 * u_height) - (5 * u_age) - 161
                
            multipliers = {"Sedentary": 1.2, "Lightly Active": 1.375, "Moderately Active": 1.55, "Very Active": 1.725}
            tdee = bmr * multipliers[activity_level]
            
            st.write(f"**BMR (Resting):** {int(bmr)} kcal")
            st.metric("TDEE (Maintenance):", f"{int(tdee)} kcal")
            st.info("To lose fat, eat ~500 kcal below maintenance. To gain muscle, eat ~300 kcal above.")
            
            if st.button("Set as my Daily Goal"):
                st.session_state.user_profile['calorie_goal'] = int(tdee - 500)
                st.session_state.goal_input = int(tdee - 500)
                save_calorie_goal()
                st.rerun()

        with st.expander("📉 Body Fat % Estimator"):
            gender_num = 1 if u_gender == "Male" else 0
            body_fat_pct = (1.20 * bmi) + (0.23 * u_age) - (10.8 * gender_num) - 5.4
            st.metric("Estimated Body Fat", f"{body_fat_pct:.1f}%")
            
            if u_gender == "Male":
                if body_fat_pct < 6: st.write("Category: Essential Fat")
                elif body_fat_pct < 14: st.write("Category: Athletes")
                elif body_fat_pct < 18: st.write("Category: Fitness")
                elif body_fat_pct < 25: st.write("Category: Average")
                else: st.write("Category: Obese")
            else:
                if body_fat_pct < 14: st.write("Category: Essential Fat")
                elif body_fat_pct < 21: st.write("Category: Athletes")
                elif body_fat_pct < 25: st.write("Category: Fitness")
                elif body_fat_pct < 32: st.write("Category: Average")
                else: st.write("Category: Obese")

    # ==========================================
    #               MAIN DASHBOARD
    # ==========================================
    current_goal = st.session_state.get('goal_input', st.session_state.user_profile.get('calorie_goal', 2000))

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
        
        save_daily_log(st.session_state.username, st.session_state.food_log)
        st.toast(f"🔥 Added {grams_eaten}g of {selected_dish}! (+{int(calories_added)} kcal)", icon="🔥")
        st.rerun()

    st.divider()
    st.subheader("📝 Today's Log")

    if len(st.session_state.food_log) > 0:
        log_df = pd.DataFrame(st.session_state.food_log)
        log_df['Calories (kcal)'] = log_df['Calories (kcal)'].apply(lambda x: round(x))
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        
        if st.button("🔄 Reset Entire Day", use_container_width=True):
            st.session_state.food_log = []
            st.session_state.total_calories = 0.0
            save_daily_log(st.session_state.username, st.session_state.food_log)
            st.rerun()
    else:
        st.info("No food logged yet today. Time to eat!")
