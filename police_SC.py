import streamlit as st
import pandas as pd
import mysql.connector as conn
from datetime import datetime
import plotly.express as px 
import random

def create_connection():
    connection = None
    try:
       mydb = conn.connect(
           host="localhost",
           user="root",
           password="Sql@pass3",
           database="Police_SC"
       )
       return mydb
    except Exception as e:
       st.error(f"Error: {e}")          
       return connection

def fetch_data(query):
    connection = create_connection()
    if connection:
        cur= connection.cursor()
        cur.execute(query)
        data = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(data, columns=columns)
        cur.close()
        connection.close()
        return df
    else:
        return pd.DataFrame()
    st.sidebar.header("Filters")
#Streamlit 
# Streamlit sidebar filters
st.sidebar.header("Filters")

# Country filter
country_df = fetch_data("SELECT DISTINCT country_name FROM traffic_stops")
country_filter = st.sidebar.multiselect(
    "Select Country",
    options=country_df['country_name'].tolist()
)

# Gender filter
gender_df = fetch_data("SELECT DISTINCT driver_gender FROM traffic_stops")
gender_filter = st.sidebar.multiselect(
    "Select Gender",
    options=gender_df['driver_gender'].tolist()
)

# Age filter
age_filter = st.sidebar.slider(
    "Select Driver Age Range",
    16, 100, (18, 40)
)
#main layout
st.set_page_config(page_title='SECURE CHECK DASHBOARD', layout='wide')
st.title(" Digital Ledger for Police Post ")
st.header('Logs & Analytics')
query='SELECT * FROM traffic_stops'
data=fetch_data(query)
st.dataframe(data)


# Base Query
base_query = "SELECT * FROM traffic_stops WHERE 1=1"

if country_filter:
    base_query += f" AND country_name IN ({','.join(['%s']*len(country_filter))})"
if gender_filter:
    base_query += f" AND driver_gender IN ({','.join(['%s']*len(gender_filter))})"
base_query += " AND driver_age BETWEEN %s AND %s"

# Combine filter values
params = tuple(country_filter + gender_filter + list(age_filter))
df = fetch_data(base_query % params)

st.title("Traffic Stop Dashboard - Medium Queries")

# Medium-level queries dictionary
queries = {
    "Top 10 vehicles involved in drug-related stops": """
        SELECT vehicle_number, COUNT(*) AS drug_related_count
        FROM traffic_stops
        WHERE drugs_related_stop = 1
        GROUP BY vehicle_number
        ORDER BY drug_related_count DESC
        LIMIT 10
    """,
    
    "Vehicles most frequently searched": """
        SELECT vehicle_number, COUNT(*) AS search_count
        FROM traffic_stops
        WHERE search_conducted = 1
        GROUP BY vehicle_number
        ORDER BY search_count DESC
        LIMIT 10
    """,
    
    "Driver age group with highest arrest rate": """
        SELECT FLOOR(driver_age/10)*10 AS age_group, 
               ROUND(SUM(is_arrested)/COUNT(*)*100,2) AS arrest_rate
        FROM traffic_stops
        GROUP BY age_group
        ORDER BY arrest_rate DESC
        LIMIT 1
    """,
    
    "Gender distribution of drivers stopped in each country": """
        SELECT country_name, driver_gender, COUNT(*) AS count
        FROM traffic_stops
        GROUP BY country_name, driver_gender
        ORDER BY country_name, driver_gender
    """,
    
    "Race and gender combination with highest search rate": """
        SELECT driver_race, driver_gender, ROUND(SUM(search_conducted)/COUNT(*)*100,2) AS search_rate
        FROM traffic_stops
        GROUP BY driver_race, driver_gender
        ORDER BY search_rate DESC
        LIMIT 5
    """,
    
    "Time of day with most traffic stops": """
        SELECT HOUR(stop_datetime) AS hour_of_day, COUNT(*) AS stop_count
        FROM traffic_stops
        GROUP BY hour_of_day
        ORDER BY stop_count DESC
    """,
    
    "Average stop duration for different violations": """
        SELECT violation, AVG(CAST(SUBSTRING_INDEX(stop_duration, '-', -1) AS UNSIGNED)) AS avg_duration_minutes
        FROM traffic_stops
        GROUP BY violation
        ORDER BY avg_duration_minutes DESC
    """,
    
    "Are stops during the night more likely to lead to arrests?": """
        SELECT ROUND(SUM(is_arrested)/COUNT(*)*100,2) AS night_arrest_rate
        FROM traffic_stops
        WHERE HOUR(stop_datetime) >= 20 OR HOUR(stop_datetime) <= 5
    """,
    
    "Violations most associated with searches or arrests": """
        SELECT violation, SUM(search_conducted) AS total_searches, SUM(is_arrested) AS total_arrests
        FROM traffic_stops
        GROUP BY violation
        ORDER BY total_arrests DESC, total_searches DESC
        LIMIT 10
    """,
    
    "Violations most common among younger drivers (<25)": """
        SELECT violation, COUNT(*) AS count
        FROM traffic_stops
        WHERE driver_age < 25
        GROUP BY violation
        ORDER BY count DESC
        LIMIT 10
    """,
    
    "Violations that rarely result in search or arrest": """
        SELECT violation, COUNT(*) AS count
        FROM traffic_stops
        WHERE search_conducted = 0 AND is_arrested = 0
        GROUP BY violation
        ORDER BY count ASC
        LIMIT 10
    """,
    
    "Countries with highest rate of drug-related stops": """
        SELECT country_name, COUNT(*) AS drug_stops
        FROM traffic_stops
        WHERE drugs_related_stop = 1
        GROUP BY country_name
        ORDER BY drug_stops DESC
        LIMIT 10
    """,
    
    "Arrest rate by country and violation": """
        SELECT country_name, violation, ROUND(SUM(is_arrested)/COUNT(*)*100,2) AS arrest_rate
        FROM traffic_stops
        GROUP BY country_name, violation
        ORDER BY arrest_rate DESC
    """,
    
    "Country with most stops with search conducted": """
        SELECT country_name, COUNT(*) AS search_count
        FROM traffic_stops
        WHERE search_conducted = 1
        GROUP BY country_name
        ORDER BY search_count DESC
        LIMIT 10
    """
}


selected_query = st.selectbox("Select a Medium Query", list(queries.keys()))

if st.button("Run Query"):
    df_result = fetch_data(queries[selected_query])
    st.subheader("Query Result")
    st.dataframe(df_result)
    
    # Safe visualization
    if not df_result.empty:
        numeric_cols = df_result.select_dtypes(include=['int64', 'float64']).columns.tolist()
        if numeric_cols:
            st.subheader("Visualization")
            non_numeric_cols = df_result.select_dtypes(exclude=['int64', 'float64']).columns.tolist()
            if non_numeric_cols:
                x_col = non_numeric_cols[0]
                y_col = numeric_cols[0]
                st.bar_chart(df_result.set_index(x_col)[y_col])
            else:
                st.bar_chart(df_result[numeric_cols[0]])


st.title(" Complex SQL Analytics Dashboard")

queries = {
    "Yearly Breakdown of Stops and Arrests by Country": """
        SELECT 
            country_name,
            YEAR(stop_datetime) AS year,
            COUNT(*) AS total_stops,
            SUM(is_arrested) AS total_arrests,
            ROUND(SUM(is_arrested)/COUNT(*)*100,2) AS arrest_rate,
            RANK() OVER (PARTITION BY country_name ORDER BY COUNT(*) DESC) AS year_rank
        FROM traffic_stops
        GROUP BY country_name, year
        ORDER BY country_name, year;
    """,

    " Driver Violation Trends Based on Age and Race": """
        SELECT 
            t.driver_race,
            FLOOR(t.driver_age/10)*10 AS age_group,
            v.violation,
            COUNT(*) AS violation_count
        FROM traffic_stops t
        JOIN (
            SELECT violation
            FROM traffic_stops
            GROUP BY violation
        ) v ON t.violation = v.violation
        GROUP BY t.driver_race, age_group, v.violation
        ORDER BY violation_count DESC
        LIMIT 20;
    """,

    " Time Period Analysis of Stops (Year, Month, Hour)": """
        SELECT 
            YEAR(stop_datetime) AS year,
            MONTH(stop_datetime) AS month,
            HOUR(stop_datetime) AS hour,
            COUNT(*) AS total_stops
        FROM traffic_stops
        GROUP BY year, month, hour
        ORDER BY year, month, hour;
    """,

    "Violations with High Search and Arrest Rates": """
        SELECT 
            violation,
            COUNT(*) AS total_stops,
            SUM(search_conducted) AS total_searches,
            SUM(is_arrested) AS total_arrests,
            ROUND(SUM(search_conducted)/COUNT(*)*100,2) AS search_rate,
            ROUND(SUM(is_arrested)/COUNT(*)*100,2) AS arrest_rate,
            RANK() OVER (ORDER BY SUM(is_arrested)/COUNT(*) DESC) AS arrest_rank
        FROM traffic_stops
        GROUP BY violation
        HAVING total_stops > 10
        ORDER BY arrest_rate DESC
        LIMIT 20;
    """,

    " Driver Demographics by Country (Age, Gender, Race)": """
        SELECT 
            country_name,
            driver_gender,
            driver_race,
            ROUND(AVG(driver_age),1) AS avg_age,
            COUNT(*) AS total_drivers
        FROM traffic_stops
        GROUP BY country_name, driver_gender, driver_race
        ORDER BY country_name, total_drivers DESC;
    """,

    " Top 5 Violations with Highest Arrest Rates": """
        SELECT 
            violation,
            COUNT(*) AS total_stops,
            SUM(is_arrested) AS total_arrests,
            ROUND(SUM(is_arrested)/COUNT(*)*100,2) AS arrest_rate
        FROM traffic_stops
        GROUP BY violation
        HAVING total_stops > 10
        ORDER BY arrest_rate DESC
        LIMIT 5;
    """
}

selected_query = st.selectbox(" Choose a Complex Query", list(queries.keys()))
if st.button("Execute Complex Query"):
    df_result = fetch_data(queries[selected_query])
    st.subheader(" Query Results")
    st.dataframe(df_result, use_container_width=True)



#police log & Prediction
def insert_log(data):
    connection = create_connection()
    cursor = connection.cursor()
    query = """
    INSERT INTO traffic_stops (
        country_name, driver_gender, driver_age_raw, driver_age,
        driver_race, violation_raw, violation, search_conducted, search_type,
        stop_outcome, is_arrested, stop_duration, drugs_related_stop, vehicle_number, stop_datetime
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, data)
    connection.commit()
    cursor.close()
    connection.close()
    st.success("✅ New police log added successfully!")


st.title(" Add New Police Log")

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
    stop_datetime = st.date_input("Stop Date")  
    stop_time = st.time_input("Stop Time")
    stop_datetime_combined = datetime.combine(stop_datetime, stop_time)

    submit_button = st.form_submit_button("Submit Log")
    
    if submit_button:
       
        new_data = (
            country_name, driver_gender, driver_age,
            violation, int(search_conducted), search_type,
            stop_outcome, int(is_arrested), stop_duration, int(drugs_related_stop),
            vehicle_number, stop_datetime_combined
        )
        insert_log(new_data)

       
        narrative = (
            f" A {driver_age}-year-old {driver_gender.lower()} driver was stopped for {violation} at "
            f"{stop_datetime_combined.strftime('%I:%M %p')}. "
            f"{'A search was conducted' if search_conducted else 'No search was conducted'}, "
            f"and they received a {stop_outcome.lower()}. "
            f"The stop lasted {stop_duration if stop_duration else 'N/A'} "
            f"and {'was' if drugs_related_stop else 'was not'} drug-related."
        )

        st.info(narrative)