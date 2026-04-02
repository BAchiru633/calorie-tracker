import streamlit as st
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="Indian Calorie Tracker", page_icon="🍛", layout="wide")
st.title("🍛 Complete Indian Calorie Tracker")

# --- 1. FULL FOOD DATABASE (Per 100g) ---
@st.cache_data
def load_data():
    try:
        # Load the CSV
        df = pd.read_csv('indian_food_db.csv')
        
        # Clean the column names (removes hidden spaces that cause KeyErrors)
        df.columns = df.columns.str.strip()
        
        # Failsafe 1: Standardize the 'Dish' column name
        if 'Dish' not in df.columns:
            dish_col = [col for col in df.columns if any(keyword in col.lower() for keyword in ['dish', 'food', 'name', 'item'])]
            if dish_col:
                df.rename(columns={dish_col[0]: 'Dish'}, inplace=True)
            else:
                df.rename(columns={df.columns[0]: 'Dish'}, inplace=True)

        # Failsafe 2: Standardize the calorie column name just in case
        if 'Calories_per_100g' not in df.columns:
            cal_col = [col for col in df.columns if 'calorie' in col.lower() or 'kcal' in col.lower()]
            if cal_col:
                df.rename(columns={cal_col[0]: 'Calories_per_100g'}, inplace=True)
        
        # --- THE FIX: Force the calories column to be purely numeric ---
        # 1. Convert to string temporarily to use regex.
        # 2. Strip out any letters, spaces, or commas (e.g. "150 kcal" becomes "150").
        # 3. Convert back to a pure float number. If it fails, make it a 0.
        df['Calories_per_100g'] = df['Calories_per_100g'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df['Calories_per_100g'] = pd.to_numeric(df['Calories_per_100g'], errors='coerce').fillna(0)
                
        return df, True
        
    except Exception as e:
        # FALLBACK: If the CSV is missing or broken, use this instead of crashing
        fallback_data = {
            "Dish": ["Plain Idli", "Plain Dosa", "Chicken Biryani", "Dal Tadka", "Paneer Butter Masala", "Roti/Phulka", "Egg Fried Rice", "Prawns Curry"],
            "Category": ["Breakfast", "Breakfast", "Rice", "Dal & Rasam", "Veg Curries", "Breads", "Rice", "Non-Veg"],
            "Calories_per_100g": [130, 168, 180, 125, 350, 297, 175, 120]
        }
        return pd.DataFrame(fallback_data), False

# Load the database
df, using_csv = load_data()

# --- 2. INITIALIZE MEMORY (SESSION STATE) ---
if 'food_log' not in st.session_state:
    st.session_state.food_log = []

if 'total_calories' not in st.session_state:
    st.session_state.total_calories = 0.0

# --- 3. SIDEBAR: GOAL SETTING ---
st.sidebar.header("🎯 Daily Goal")
calorie_goal = st.sidebar.number_input("Set Calorie Goal", min_value=1000, max_value=5000, value=2500, step=100)

# --- 4. PROGRESS METER ---
st.header("📊 Today's Progress")

# Calculate how full the bar should be (cap at 1.0 to prevent bar errors)
progress_percentage = min(st.session_state.total_calories / calorie_goal, 1.0)
calories_remaining = calorie_goal - st.session_state.total_calories

if progress_percentage >= 1.0:
    st.error(f"Goal Reached / Exceeded! Total: {st.session_state.total_calories:.0f} kcal")
    st.progress(1.0)
else:
    st.metric(label="Calories Consumed", value=f"{st.session_state.total_calories:.0f} kcal", delta=f"{calories_remaining:.0f} kcal remaining")
    st.progress(progress_percentage)

st.divider()

# --- 5. FOOD LOGGER ---
st.header("🍽️ Log a Meal")
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Safely select a dish
    selected_dish = st.selectbox("Search for a dish:", df['Dish'].sort_values())
    
with col2:
    grams_eaten = st.number_input("Amount (grams):", min_value=10, max_value=1000, value=100, step=10)

with col3:
    st.write("") # Spacing alignment
    st.write("")
    if st.button("➕ Log Food", use_container_width=True):
        # Calculate precise calories
        dish_stats = df[df['Dish'] == selected_dish].iloc[0]
        
        # Because we cleaned the column above, this math will now work perfectly!
        calories_added = (dish_stats['Calories_per_100g'] / 100.0) * grams_eaten
        
        # Save to memory
        st.session_state.food_log.append({
            "Dish": selected_dish,
            "Amount (g)": grams_eaten,
            "Calories (kcal)": calories_added
        })
        st.session_state.total_calories += calories_added
        st.rerun() # Refresh the page to update the meter

# --- 6. LOG HISTORY & RESET ---
st.divider()
col_log, col_reset = st.columns([4, 1])

with col_log:
    st.subheader("📝 Today's Log")
    if len(st.session_state.food_log) > 0:
        log_df = pd.DataFrame(st.session_state.food_log)
        # Clean up decimal points for display
        log_df['Calories (kcal)'] = log_df['Calories (kcal)'].apply(lambda x: round(x))
        st.dataframe(log_df, use_container_width=True, hide_index=True)
    else:
        st.info("No food logged yet today. Time to eat!")

with col_reset:
    st.write("") # Spacing alignment
    st.write("")
    if st.button("🔄 Reset Day", type="primary", use_container_width=True):
        st.session_state.food_log = []
        st.session_state.total_calories = 0.0
        st.rerun()
