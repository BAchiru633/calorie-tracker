import streamlit as st
import pandas as pd

st.set_page_config(page_title="Indian Calorie Tracker", layout="wide")

# --- 1. LOAD EXTERNAL DATABASE ---
@st.cache_data
def load_data():
    # Read the CSV
    df = pd.read_csv('indian_food_db.csv')
    
    # BULLETPROOF FIX: Strip any accidental spaces from the column names
    df.columns = df.columns.str.strip()
    
    return df

# --- 2. INITIALIZE MEMORY (SESSION STATE) ---
if 'log' not in st.session_state: 
    st.session_state.log = []
if 'total' not in st.session_state: 
    st.session_state.total = 0.0

# --- 3. UI LAYOUT: DASHBOARD ---
st.title("🍛 Comprehensive Indian Calorie Dashboard")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Your Profile")
    age = st.number_input("Age", value=23, min_value=15, max_value=100)
    weight = st.number_input("Weight (kg)", value=140.0, min_value=40.0)
    height = st.number_input("Height (cm)", value=183.0, min_value=100.0)
    goal = st.number_input("Daily Calorie Goal", value=2500, min_value=1000, step=100)
    
    # Body Fat Logic (Deurenberg Formula)
    bmi = weight / ((height/100)**2)
    bfp = (1.20 * bmi) + (0.23 * age) - 16.2
    st.metric("Estimated Body Fat %", f"{bfp:.1f}%")

with col2:
    st.subheader("Log a Meal")
    
    # Category Filter
    categories = df['Category'].dropna().unique().tolist()
    cat_filter = st.multiselect("Filter by Category (Optional)", categories)
    
    # Apply filter if user selected anything
    filtered_df = df if not cat_filter else df[df['Category'].isin(cat_filter)]
    
    # Dish Selection
    selected_dish = st.selectbox("Select Dish", filtered_df['Dish'].sort_values())
    
    # Grams Input
    grams = st.number_input("Amount (Grams)", value=100, step=50, min_value=10)
    
    # Add to Log Action
    if st.button("➕ Add to Plate", use_container_width=True):
        # Fetch calories per 100g for the selected dish from the database
        kcal_per_100g = df[df['Dish'] == selected_dish]['Calories_per_100g'].values[0]
        
        # Calculate precise calories
        cals = (kcal_per_100g / 100.0) * grams
        
        # Save to session memory
        st.session_state.log.append({
            "Dish": selected_dish, 
            "Amount (g)": grams, 
            "Calories (kcal)": cals
        })
        st.session_state.total += cals
        st.rerun()

# --- 4. PROGRESS METER & LOG HISTORY ---
st.divider()

# Calculate remaining calories and meter percentage
remaining = goal - st.session_state.total
progress_val = min(st.session_state.total / goal, 1.0)

st.subheader("📊 Today's Progress")
if progress_val >= 1.0:
    st.error(f"Goal Reached / Exceeded! Total: {st.session_state.total:.0f} kcal")
else:
    st.write(f"**Total Calories:** {st.session_state.total:.0f} / {goal} kcal ({remaining:.0f} remaining)")

st.progress(progress_val)
st.write("") # Spacing

col_log, col_reset = st.columns([4, 1])

with col_log:
    if st.session_state.log:
        # Format the dataframe for a clean display
        log_df = pd.DataFrame(st.session_state.log)
        log_df['Calories (kcal)'] = log_df['Calories (kcal)'].apply(lambda x: round(x))
        st.dataframe(log_df, use_container_width=True, hide_index=True)
    else:
        st.info("No food logged yet today. Time to eat!")

with col_reset:
    if st.button("🔄 Reset Day", type="primary", use_container_width=True):
        # Clear the memory and reset the meter
        st.session_state.log = []
        st.session_state.total = 0.0
        st.rerun()
