import streamlit as st
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="Indian Calorie Tracker", page_icon="🍛", layout="wide")
st.title("🍛 Complete Indian Calorie Tracker")

# --- 1. FULL FOOD DATABASE (Per 100g) ---
food_data = {
    "Dish": [
        # South Indian
        "Plain Idli", "Plain Dosa", "Sambar", "Uggani", "Ragi Mudde", "Egg Fried Rice", "Prawns Curry", "Palakova",
        # North Indian
        "Roti/Phulka", "Paneer Butter Masala", "Dal Makhani", "Chicken Tikka Masala", "Aloo Gobi", "Chole", "Palak Paneer"
    ],
    "Calories (kcal per 100g)": [
        130, 168, 75, 150, 115, 175, 120, 350,
        297, 350, 130, 150, 90, 150, 230
    ],
    "Region": [
        "South", "South", "South", "South", "South", "South", "South", "South",
        "North", "North", "North", "North", "North", "North", "North"
    ]
}
df_food = pd.DataFrame(food_data)

# --- 2. INITIALIZE MEMORY (SESSION STATE) ---
if 'food_log' not in st.session_state:
    st.session_state.food_log = []

if 'total_calories' not in st.session_state:
    st.session_state.total_calories = 0.0

# --- 3. SIDEBAR: GOAL SETTING ---
st.sidebar.header("🎯 Daily Goal")
# Setting a default goal; you can adjust this daily as you progress in your fat loss phase.
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
    selected_dish = st.selectbox("Search for a dish:", df_food['Dish'].sort_values())
    
with col2:
    grams_eaten = st.number_input("Amount (grams):", min_value=10, max_value=1000, value=100, step=10)

with col3:
    st.write("") # Spacing alignment
    st.write("")
    if st.button("➕ Log Food", use_container_width=True):
        # Calculate precise calories
        dish_stats = df_food[df_food['Dish'] == selected_dish].iloc[0]
        calories_added = (dish_stats['Calories (kcal per 100g)'] / 100.0) * grams_eaten
        
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