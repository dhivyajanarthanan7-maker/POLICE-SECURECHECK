import streamlit as st
import pandas as pd
import mysql.connector as conn
from datetime import datetime
import plotly.express as px 
import random


@st.cache_data
def load_data():
    df = pd.read_csv("traffic_stops.csv", parse_dates=['stop_datetime'])
    return df

df = load_data()


# Streamlit Page Config

st.set_page_config(page_title='SECURE CHECK DASHBOARD', layout='wide')
st.title("Digital Ledger for Police Post")
st.header("Logs & Analytics")



# Apply filters
filtered_df = df.copy()
if country_filter:
    filtered_df = filtered_df[filtered_df['country_name'].isin(country_filter)]
if gender_filter:
    filtered_df = filtered_df[filtered_df['driver_gender'].isin(gender_filter)]
filtered_df = filtered_df[
    (filtered_df['driver_age'] >= age_filter[0]) &
    (filtered_df['driver_age'] <= age_filter[1])
]

# Show filtered data
st.subheader("Filtered Data")
st.dataframe(filtered_df)


st.title("Traffic Stop Dashboard - Medium Queries")

medium_queries = {
    "Top 10 vehicles involved in drug-related stops": lambda df: df[df['drugs_related_stop']==1]['vehicle_number'].value_counts().head(10),
    
    "Vehicles most frequently searched": lambda df: df[df['search_conducted']==1]['vehicle_number'].value_counts().head(10),
    
    "Driver age group with highest arrest rate": lambda df: df.groupby(df['driver_age']//10*10).agg(arrest_rate=('is_arrested', 'mean')).sort_values('arrest_rate', ascending=False).head(1)*100,
    
    "Gender distribution of drivers stopped in each country": lambda df: df.groupby(['country_name','driver_gender']).size().unstack(fill_value=0),
    
    "Race and gender combination with highest search rate": lambda df: df.groupby(['driver_race','driver_gender']).agg(search_rate=('search_conducted','mean')).sort_values('search_rate', ascending=False).head(5)*100,
    
    "Time of day with most traffic stops": lambda df: df.groupby(df['stop_datetime'].dt.hour).size().sort_values(ascending=False),
    
    "Average stop duration for different violations": lambda df: df.assign(stop_duration_min=df['stop_duration'].str.extract(r'(\d+)-?(\d+)?').astype(float).mean(axis=1)).groupby('violation').stop_duration_min.mean().sort_values(ascending=False),
    
    "Are stops during the night more likely to lead to arrests?": lambda df: df[((df['stop_datetime'].dt.hour >= 20) | (df['stop_datetime'].dt.hour <= 5))]['is_arrested'].mean()*100,
    
    "Violations most associated with searches or arrests": lambda df: df.groupby('violation').agg(total_searches=('search_conducted','sum'), total_arrests=('is_arrested','sum')).sort_values(['total_arrests','total_searches'], ascending=False).head(10),
    
    "Violations most common among younger drivers (<25)": lambda df: df[df['driver_age']<25]['violation'].value_counts().head(10),
    
    "Violations that rarely result in search or arrest": lambda df: df[(df['search_conducted']==0) & (df['is_arrested']==0)]['violation'].value_counts().head(10),
    
    "Countries with highest rate of drug-related stops": lambda df: df[df['drugs_related_stop']==1]['country_name'].value_counts().head(10),
    
    "Arrest rate by country and violation": lambda df: df.groupby(['country_name','violation']).agg(arrest_rate=('is_arrested','mean')).sort_values('arrest_rate', ascending=False)*100,
    
    "Country with most stops with search conducted": lambda df: df[df['search_conducted']==1]['country_name'].value_counts().head(10)
}

selected_query = st.selectbox("Select a Medium Query", list(medium_queries.keys()))

if st.button("Run Medium Query"):
    result = medium_queries[selected_query](filtered_df)
    st.subheader("Query Result")
    st.dataframe(result)
    
    # Visualization
    if isinstance(result, pd.Series):
        st.bar_chart(result)
    elif isinstance(result, pd.DataFrame):
        numeric_cols = result.select_dtypes(include=['float','int']).columns
        if len(numeric_cols) > 0:
            st.bar_chart(result[numeric_cols[0]])

# -----------------------------
# Add New Police Log
# -----------------------------
st.title("Add New Police Log")

with st.form(key='police_log_form'):
    st.subheader("Driver & Violation Details")
    country_name = st.text_input("Country Name")
    driver_gender = st.selectbox("Driver Gender", ["Male", "Female", "Other"])
    driver_age = st.number_input("Driver Age", min_value=0, max_value=120, value=27)
    violation = st.selectbox("Violation", ["Speeding", "DUI", "Equipment", "Other"])
    search_conducted = st.checkbox("Search Conducted?")
    search_type = st.text_input("Search Type (if any)")
    stop_outcome = st.selectbox("Stop Outcome", ["Citation", "Warning", "Arrest"])
    is_arrested = st.checkbox("Arrested?")
    stop_duration = st.text_input("Stop Duration (e.g., 6-15 minutes)")
    drugs_related_stop = st.checkbox("Drugs Related Stop?")
    vehicle_number = st.text_input("Vehicle Number")
    stop_date = st.date_input("Stop Date")
    stop_time = st.time_input("Stop Time")
    stop_datetime_combined = datetime.combine(stop_date, stop_time)

    submit_button = st.form_submit_button("Submit Log")
    
    if submit_button:
        new_row = {
            "country_name": country_name,
            "driver_gender": driver_gender,
            "driver_age": driver_age,
            "driver_race": "Unknown",
            "violation_raw": violation,
            "violation": violation,
            "search_conducted": int(search_conducted),
            "search_type": search_type,
            "stop_outcome": stop_outcome,
            "is_arrested": int(is_arrested),
            "stop_duration": stop_duration,
            "drugs_related_stop": int(drugs_related_stop),
            "vehicle_number": vehicle_number,
            "stop_datetime": stop_datetime_combined
        }
        # Append new row to DataFrame
        filtered_df = pd.concat([filtered_df, pd.DataFrame([new_row])], ignore_index=True)
        st.success("✅ New police log added successfully!")
        
        narrative = (
            f"A {driver_age}-year-old {driver_gender.lower()} driver was stopped for {violation} at "
            f"{stop_datetime_combined.strftime('%I:%M %p')}. "
            f"{'A search was conducted' if search_conducted else 'No search was conducted'}, "
            f"and they received a {stop_outcome.lower()}. "
            f"The stop lasted {stop_duration if stop_duration else 'N/A'} "
            f"and {'was' if drugs_related_stop else 'was not'} drug-related."
        )
        st.info(narrative)
