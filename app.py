import streamlit as st
import pandas as pd

st.set_page_config(page_title="Indian Calorie & Body Fat Tracker", page_icon="🍛", layout="wide")

# --- 1. ROBUST DATA LOADER ---
# This function is bulletproofed against KeyErrors and missing files
@st.cache_data
def load_data():
    try:
        # Load the CSV
        df = pd.read_csv('indian_food_db.csv')
        
        # Clean the column names (removes hidden spaces that cause KeyErrors)
        df.columns = df.columns.str.strip()
        
        # Failsafe: Standardize the calorie column name just in case
        if 'Calories_per_100g' not in df.columns:
            cal_col = [col for col in df.columns if 'calorie' in col.lower() or 'kcal' in col.lower()]
            if cal_col:
                df.rename(columns={cal_col[0]: 'Calories_per_100g'}, inplace=True)
                
        return df, True
        
    except Exception as e:
        # FALLBACK: If the CSV is missing or broken, the app will use this instead of crashing
        fallback_data = {
            "Dish": ["Plain Idli", "Plain Dosa", "Chicken Biryani", "Dal Tadka", "Paneer Butter Masala", "Roti/Phulka", "Egg Fried Rice", "Prawns Curry"],
            "Category": ["Breakfast", "Breakfast", "Rice", "Dal & Rasam", "Veg Curries", "Breads", "Rice", "Non-Veg"],
            "Calories_per_100g": [130, 168, 180, 125, 350, 297, 175, 120]
        }
        return pd.DataFrame(fallback_data), False

# Load the database
df, using_csv = load_data()

# --- 2. INITIALIZE DAILY TRACKER MEMORY ---
if 'food_log' not in st.session_state:
    st.session_state.food_log = []
if 'total_calories' not in st.session_state:
    st.session_state.total_calories = 0.0

# --- 3. MAIN UI LAYOUT ---
st.title("🍛 Indian Calorie & Body Fat Tracker")

if not using_csv:
    st.warning("⚠️ 'indian_food_db.csv' could not be loaded. Running on backup sample data. Please ensure the CSV is in the same folder as app.py.")

col1, col2 = st.columns([1, 2])

# --- LEFT COLUMN: PROFILE & BODY FAT ---
with col1:
    st.header("👤 Your Profile")
    with st.container(border=True):
        # Added gender toggle for accurate Deurenberg calculation
        gender = st.radio("Gender", ["Male", "Female"], horizontal=True)
        age = st.number_input("Age", min_value=15, max_value=100, value=23)
        weight = st.number_input("Weight (kg)", min_value=40.0, max_value=250.0, value=140.0, step=0.5)
        height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=183.0, step=1.0)
        daily_goal = st.number_input("Daily Calorie Goal (kcal)", min_value=1000, max_value=5000, value=2500, step=100)
        
        # Body Fat Math
        if height > 0 and weight > 0:
            height_m = height / 100
            bmi = weight / (height_m ** 2)
            
            # Deurenberg Formula applies different modifiers based on gender
            if gender == "Male":
                body_fat = (1.20 * bmi) + (0.23 * age) - 16.2
            else:
                body_fat = (1.20 * bmi) + (0.23 * age) - 5.4
            
            st.divider()
            st.metric("Estimated Body Fat %", f"{max(0, body_fat):.1f}%")
            st.caption(f"Current BMI: {bmi:.1f}")

# --- RIGHT COLUMN: FOOD LOGGING ---
with col2:
    st.header("🍽️ Log Indian Meals")
    with st.container(border=True):
        
        # Category Filter (Only shows if 'Category' column exists in data)
        if 'Category' in df.columns:
            categories = ["All"] + df['Category'].dropna().unique().tolist()
            selected_cat = st.selectbox("Filter by Category", categories)
            filtered_df = df if selected_cat == "All" else df[df['Category'] == selected_cat]
        else:
            filtered_df = df
            
        # Select Dish and Weight
        selected_dish = st.selectbox("Select Dish", filtered_df['Dish'].sort_values())
        grams_eaten = st.number_input("Amount Eaten (in grams)", min_value=10, max_value=2000, value=100, step=50)
        
        # Add to Plate Logic
        if st.button("➕ Add to Daily Tracker", use_container_width=True, type="primary"):
            # Extract calories per 100g securely
            dish_row = df[df['Dish'] == selected_dish].iloc[0]
            cals_per_100 = dish_row['Calories_per_100g']
            
            # Calculate exact calories for the grams eaten
            total_cals = (cals_per_100 / 100.0) * grams_eaten
            
            # Save to memory
            st.session_state.food_log.append({
                "Dish": selected_dish,
                "Amount (g)": grams_eaten,
                "Calories Added": round(total_cals)
            })
            st.session_state.total_calories += total_cals
            st.rerun()

# --- 4. DAILY DASHBOARD & LOG ---
st.divider()
st.header("📊 Today's Progress")

# Visual Meter Math
progress_fraction = st.session_state.total_calories / daily_goal
remaining_cals = max(0, daily_goal - st.session_state.total_calories)

m1, m2, m3 = st.columns(3)
m1.metric("Daily Goal", f"{daily_goal} kcal")
m2.metric("Consumed Today", f"{st.session_state.total_calories:.0f} kcal")
m3.metric("Remaining", f"{remaining_cals:.0f} kcal")

# Alert user if they overeat
if progress_fraction > 1.0:
    st.error("⚠️ You have exceeded your daily calorie goal!")
    st.progress(1.0)
else:
    st.progress(progress_fraction)

st.write("") # Spacing

# Food Log Table
col_table, col_reset = st.columns([4, 1])

with col_table:
    if st.session_state.food_log:
        st.dataframe(pd.DataFrame(st.session_state.food_log), use_container_width=True, hide_index=True)
    else:
        st.info("No food logged yet. Select a dish above to get started!")

with col_reset:
    if st.button("🗑️ Reset Day", use_container_width=True):
        st.session_state.food_log = []
        st.session_state.total_calories = 0.0
        st.rerun()
