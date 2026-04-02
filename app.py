import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Indian Calorie Tracker", page_icon="🍛", layout="centered")

# --- 1. FULL FOOD DATABASE (Per 100g) ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('indian_food_db.csv')
        df.columns = df.columns.str.strip()
        
        if 'Dish' not in df.columns:
            dish_col = [col for col in df.columns if any(keyword in col.lower() for keyword in ['dish', 'food', 'name', 'item'])]
            if dish_col:
                df.rename(columns={dish_col[0]: 'Dish'}, inplace=True)
            else:
                df.rename(columns={df.columns[0]: 'Dish'}, inplace=True)

        if 'Calories_per_100g' not in df.columns:
            cal_col = [col for col in df.columns if 'calorie' in col.lower() or 'kcal' in col.lower()]
            if cal_col:
                df.rename(columns={cal_col[0]: 'Calories_per_100g'}, inplace=True)
        
        df['Calories_per_100g'] = df['Calories_per_100g'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df['Calories_per_100g'] = pd.to_numeric(df['Calories_per_100g'], errors='coerce').fillna(0)
                
        return df, True
        
    except Exception as e:
        fallback_data = {
            "Dish": ["Plain Idli", "Plain Dosa", "Chicken Biryani", "Dal Tadka", "Paneer Butter Masala", "Roti/Phulka", "Egg Fried Rice", "Prawns Curry"],
            "Category": ["Breakfast", "Breakfast", "Rice", "Dal & Rasam", "Veg Curries", "Breads", "Rice", "Non-Veg"],
            "Calories_per_100g": [130, 168, 180, 125, 350, 297, 175, 120]
        }
        return pd.DataFrame(fallback_data), False

df, using_csv = load_data()

# --- 2. PERMANENT MEMORY (SAVE / LOAD) ---
LOG_FILE = "my_daily_log.csv"

def load_daily_log():
    """Loads the saved food log from the computer, if it exists."""
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE).to_dict('records')
    return []

def save_daily_log(log_list):
    """Saves the current food log to the computer so it survives refreshes."""
    if len(log_list) > 0:
        pd.DataFrame(log_list).to_csv(LOG_FILE, index=False)
    else:
        # If the log is empty (e.g., we hit reset), delete the file
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)

# Initialize from the saved file instead of a blank list!
if 'food_log' not in st.session_state:
    st.session_state.food_log = load_daily_log()

if 'total_calories' not in st.session_state:
    # Recalculate total calories based on the saved log
    st.session_state.total_calories = sum([item['Calories (kcal)'] for item in st.session_state.food_log])


st.title("🍛 Complete Indian Calorie Tracker")

# --- 3. SIDEBAR: GOAL SETTING ---
with st.sidebar:
    st.header("🎯 Daily Goal")
    calorie_goal = st.number_input("Set Calorie Goal", min_value=1000, max_value=5000, value=2500, step=100)
    st.info("💡 Adjust this goal based on your current fitness targets.")

# --- 4. CIRCULAR PROGRESS METER (PLOTLY) ---
st.subheader("📊 Today's Progress")

# Determine color based on progress natively
if st.session_state.total_calories > calorie_goal:
    bar_color = "#FF4B4B" # Streamlit Native Red
elif st.session_state.total_calories > (calorie_goal * 0.8):
    bar_color = "#FFAA00" # Warning Orange
else:
    bar_color = "#00CC96" # Success Green

fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = st.session_state.total_calories,
    number = {'suffix': " kcal", 'font': {'size': 45}},
    title = {'text': f"Goal: {calorie_goal} kcal", 'font': {'size': 20}},
    gauge = {
        'axis': {'range': [0, calorie_goal], 'tickwidth': 1},
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
    
    # NEW: Save to file instantly!
    save_daily_log(st.session_state.food_log)
    
    # NATIVE STREAMLIT ANIMATION / NOTIFICATION
    st.toast(f"🔥 Added {grams_eaten}g of {selected_dish}! (+{int(calories_added)} kcal)", icon="🔥")
    st.rerun()

# --- 6. LOG HISTORY & RESET ---
st.divider()
st.subheader("📝 Today's Log")

if len(st.session_state.food_log) > 0:
    log_df = pd.DataFrame(st.session_state.food_log)
    log_df['Calories (kcal)'] = log_df['Calories (kcal)'].apply(lambda x: round(x))
    
    # Use native data editor for a cleaner look
    st.dataframe(log_df, use_container_width=True, hide_index=True)
    
    if st.button("🔄 Reset Entire Day", use_container_width=True):
        st.session_state.food_log = []
        st.session_state.total_calories = 0.0
        # NEW: Delete the file so it actually resets!
        save_daily_log(st.session_state.food_log)
        st.rerun()
else:
    st.info("No food logged yet today. Time to eat!")
