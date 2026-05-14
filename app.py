import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Connect to SQLite database (creates 'techwheels.db' automatically)
conn = sqlite3.connect('techwheels.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    """Initializes tables and injects expanded sample data for the demo."""
    c.executescript('''
        CREATE TABLE IF NOT EXISTS HUB (Hub_ID INTEGER PRIMARY KEY, Name TEXT, Total_Spots INTEGER);
        CREATE TABLE IF NOT EXISTS MEMBER (CUNY_ID INTEGER PRIMARY KEY, Full_Name TEXT, Account_Status TEXT);
        CREATE TABLE IF NOT EXISTS VEHICLE (Vehicle_ID INTEGER PRIMARY KEY, Make TEXT, Model TEXT, Vehicle_Type TEXT, Status TEXT, Parked_Hub_ID INTEGER);
        CREATE TABLE IF NOT EXISTS RESERVATION (Reservation_ID INTEGER PRIMARY KEY AUTOINCREMENT, CUNY_ID INTEGER, Vehicle_ID INTEGER, Exp_Return DATETIME, Act_Return DATETIME);
    ''')
    
    # Insert Mock Data if db is empty
    c.execute("SELECT COUNT(*) FROM HUB")
    if c.fetchone()[0] == 0:
        c.executescript(f'''
            -- Insert 4 Hubs
            INSERT INTO HUB VALUES 
            (1, 'Main Quad Hub', 20), (2, 'Library Hub', 15),
            (3, 'Student Union Hub', 30), (4, 'North Dorms Hub', 10);

            -- Insert 6 Members
            INSERT INTO MEMBER VALUES 
            (24635012, 'Biraj Guragai', 'Active'), (99887766, 'Jane Doe', 'Active'),
            (11223344, 'John Smith', 'Suspended'), (55667788, 'Alice Johnson', 'Active'),
            (44556677, 'Bob Williams', 'Active'), (33445566, 'Charlie Brown', 'Active');

            -- Insert 12 Vehicles
            INSERT INTO VEHICLE VALUES 
            (101, 'Segway', 'Ninebot Max', 'Scooter', 'Available', 1), 
            (102, 'Segway', 'Ninebot Max', 'Scooter', 'Available', 1),
            (103, 'Niu', 'KQi3 Pro', 'Scooter', 'Checked Out', NULL),
            (201, 'Toyota', 'Prius', 'Hybrid Car', 'Checked Out', NULL),
            (202, 'Honda', 'Accord Hybrid', 'Hybrid Car', 'Available', 2),
            (203, 'Ford', 'Escape Hybrid', 'Hybrid Car', 'Under Maintenance', NULL),
            (301, 'Tesla', 'Model 3', 'Electric Car', 'Available', 3),
            (302, 'Tesla', 'Model Y', 'Electric Car', 'Available', 3),
            (303, 'Nissan', 'Leaf', 'Electric Car', 'Checked Out', NULL),
            (401, 'Rad Power', 'RadRunner', 'E-Bike', 'Available', 4),
            (402, 'Rad Power', 'RadRunner', 'E-Bike', 'Available', 4),
            (403, 'Aventon', 'Pace 500', 'E-Bike', 'Checked Out', NULL);

            -- Insert Reservations 
            -- Overdue
            INSERT INTO RESERVATION (CUNY_ID, Vehicle_ID, Exp_Return, Act_Return) 
            VALUES (99887766, 201, '{(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")}', NULL);
            INSERT INTO RESERVATION (CUNY_ID, Vehicle_ID, Exp_Return, Act_Return) 
            VALUES (55667788, 103, '{(datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")}', NULL);

            -- Active/On-Time
            INSERT INTO RESERVATION (CUNY_ID, Vehicle_ID, Exp_Return, Act_Return) 
            VALUES (44556677, 303, '{(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")}', NULL);
            INSERT INTO RESERVATION (CUNY_ID, Vehicle_ID, Exp_Return, Act_Return) 
            VALUES (33445566, 403, '{(datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")}', NULL);
        ''')
        conn.commit()

init_db()

# --- GUI Layout ---
st.set_page_config(page_title="TechWheels System", layout="wide")
st.title("🚗 TechWheels Database System")
st.sidebar.header("Operations Menu")
menu = st.sidebar.radio("Navigate", ["Dashboard & Reports", "Register Member", "Add/Update Vehicle", "Retire Vehicle"])

# --- 1. READ / REPORTS ---
if menu == "Dashboard & Reports":
    st.header("System Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Available Vehicles")
        df_avail = pd.read_sql_query("SELECT Vehicle_ID, Make, Model, Vehicle_Type, Parked_Hub_ID FROM VEHICLE WHERE Status = 'Available'", conn)
        st.dataframe(df_avail, use_container_width=True)
        
    with col2:
        st.subheader("🚨 Overdue Tracking Report")
        query = '''
            SELECT m.Full_Name, v.Vehicle_ID, v.Make, r.Exp_Return 
            FROM RESERVATION r
            JOIN MEMBER m ON r.CUNY_ID = m.CUNY_ID
            JOIN VEHICLE v ON r.Vehicle_ID = v.Vehicle_ID
            WHERE r.Act_Return IS NULL AND r.Exp_Return < CURRENT_TIMESTAMP
        '''
        df_overdue = pd.read_sql_query(query, conn)
        if df_overdue.empty:
            st.success("No overdue vehicles!")
        else:
            st.error("The following vehicles are overdue:")
            st.dataframe(df_overdue, use_container_width=True)

# --- 2. CREATE ---
elif menu == "Register Member":
    st.header("Register New Member")
    with st.form("member_form"):
        cuny_id = st.number_input("CUNY ID", min_value=10000000, max_value=99999999)
        name = st.text_input("Full Name")
        submit = st.form_submit_button("Register")
        if submit:
            try:
                c.execute("INSERT INTO MEMBER (CUNY_ID, Full_Name, Account_Status) VALUES (?, ?, 'Active')", (cuny_id, name))
                conn.commit()
                st.success(f"Member {name} registered successfully!")
            except sqlite3.IntegrityError:
                st.error("Error: CUNY ID already exists.")

# --- 3. CREATE / UPDATE ---
elif menu == "Add/Update Vehicle":
    st.header("Fleet Management")
    tab1, tab2 = st.tabs(["Add New Vehicle", "Update Vehicle Status"])
    
    with tab1:
        with st.form("add_veh_form"):
            v_id = st.number_input("Vehicle ID", min_value=1)
            make = st.text_input("Make")
            model = st.text_input("Model")
            v_type = st.selectbox("Type", ["Scooter", "Electric Car", "Hybrid Car", "E-Bike"])
            hub = st.number_input("Starting Hub ID", min_value=1, max_value=4)
            if st.form_submit_button("Add to Fleet"):
                try:
                    c.execute("INSERT INTO VEHICLE VALUES (?, ?, ?, ?, 'Available', ?)", (v_id, make, model, v_type, hub))
                    conn.commit()
                    st.success("Vehicle Added!")
                except sqlite3.IntegrityError:
                    st.error("Vehicle ID exists.")
                    
    with tab2:
        df_v = pd.read_sql_query("SELECT Vehicle_ID, Make, Model, Status FROM VEHICLE", conn)
        st.dataframe(df_v)
        v_update = st.number_input("ID to Update", min_value=1)
        new_stat = st.selectbox("New Status", ["Available", "Checked Out", "Under Maintenance"])
        if st.button("Update Status"):
            c.execute("UPDATE VEHICLE SET Status = ? WHERE Vehicle_ID = ?", (new_stat, v_update))
            conn.commit()
            st.success("Status Updated! Check the Dashboard.")

# --- 4. DELETE ---
elif menu == "Retire Vehicle":
    st.header("Retire Vehicle (Delete)")
    df_v = pd.read_sql_query("SELECT Vehicle_ID, Make, Model FROM VEHICLE", conn)
    st.dataframe(df_v)
    v_delete = st.number_input("ID to Retire", min_value=1)
    if st.button("Delete from Database"):
        c.execute("DELETE FROM VEHICLE WHERE Vehicle_ID = ?", (v_delete,))
        conn.commit()
        st.warning(f"Vehicle {v_delete} permanently removed.")