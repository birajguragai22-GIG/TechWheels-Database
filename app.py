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
menu = st.sidebar.radio("Navigate", ["Dashboard & Reports", "Register Member", "Manage Members", "Add/Update Vehicle", "Manage Trips", "Retire Vehicle"])
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

                # --- 2.5. UPDATE / DELETE MEMBERS ---
elif menu == "Manage Members":
    st.header("Manage Registered Members")
    
    # READ: Show the current member list
    st.subheader("Current Member Directory")
    df_members = pd.read_sql_query("SELECT CUNY_ID, Full_Name, Account_Status FROM MEMBER", conn)
    st.dataframe(df_members, use_container_width=True)
    
    tab1, tab2 = st.tabs(["Update Account Status", "Remove Member"])
    
    # UPDATE
    with tab1:
        st.write("Use this tool to suspend members with overdue vehicles.")
        m_id_update = st.number_input("Enter CUNY ID to Update", min_value=10000000, max_value=99999999, step=1)
        new_status = st.selectbox("New Account Status", ["Active", "Suspended", "Inactive"])
        
        if st.button("Update Member Status"):
            c.execute("UPDATE MEMBER SET Account_Status = ? WHERE CUNY_ID = ?", (new_status, m_id_update))
            conn.commit()
            st.success(f"CUNY ID {m_id_update} status changed to {new_status}!")
            
    # DELETE
    with tab2:
        st.write("⚠️ WARNING: Removing a member cannot be undone.")
        m_id_delete = st.number_input("Enter CUNY ID to Remove", min_value=10000000, max_value=99999999, step=1)
        
        if st.button("Permanently Delete Member"):
            # First, we need to delete their reservations to avoid foreign key conflicts
            c.execute("DELETE FROM RESERVATION WHERE CUNY_ID = ?", (m_id_delete,))
            # Then delete the member
            c.execute("DELETE FROM MEMBER WHERE CUNY_ID = ?", (m_id_delete,))
            conn.commit()
            st.warning(f"Member {m_id_delete} and all their trip history have been deleted.")

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
           # --- 3. MANAGE TRIPS (Unified Check-Out & Return) ---
elif menu == "Manage Trips":
    st.header("🚦 Trip Kiosk")
    st.write("Manage all vehicle check-outs and returns from this central hub.")
    
    # We use Streamlit Tabs to keep both actions on the exact same page
    tab_out, tab_in = st.tabs(["Check-Out a Vehicle", "Process a Return"])
    
    # === TAB 1: CHECK-OUT ===
    with tab_out:
        st.subheader("Start a New Trip")
        
        # 1. Fetch only Active Members
        df_active_members = pd.read_sql_query("SELECT CUNY_ID, Full_Name FROM MEMBER WHERE Account_Status = 'Active'", conn)
        
        if df_active_members.empty:
            st.error("No active members available.")
        else:
            member_options = df_active_members['CUNY_ID'].astype(str) + " - " + df_active_members['Full_Name']
            selected_member = st.selectbox("1. Select Member", member_options, key="checkout_member")
            cuny_id = int(selected_member.split(" - ")[0])
            
            # 2. ENFORCE THE RULE: Check how many active vehicles this member currently has
            c.execute("SELECT COUNT(*) FROM RESERVATION WHERE CUNY_ID = ? AND Act_Return IS NULL", (cuny_id,))
            active_trips = c.fetchone()[0]
            
            if active_trips >= 2:
                st.error(f"🛑 Limit Reached: This member currently has {active_trips} active vehicles. They cannot reserve another until they return one.")
            else:
                st.success(f"✅ Member eligible. Current active trips: {active_trips} / 2.")
                
                # 3. Only show the rest of the form if they pass the limit check
                df_avail_cars = pd.read_sql_query("SELECT Vehicle_ID, Make, Model, Parked_Hub_ID FROM VEHICLE WHERE Status = 'Available'", conn)
                if df_avail_cars.empty:
                    st.warning("No vehicles are currently available.")
                else:
                    with st.form("checkout_form"):
                        car_options = df_avail_cars['Vehicle_ID'].astype(str) + " - " + df_avail_cars['Make'] + " " + df_avail_cars['Model'] + " (Hub " + df_avail_cars['Parked_Hub_ID'].astype(str) + ")"
                        selected_car = st.selectbox("2. Select Vehicle", car_options)
                        
                        rental_hours = st.number_input("3. Rental Duration (Hours)", min_value=1, max_value=72, value=2, step=1)
                        
                        if st.form_submit_button("Start Trip"):
                            veh_id = int(selected_car.split(" - ")[0])
                            
                            # Calculates the exact due time based on right now
                            exp_return_time = (datetime.now() + timedelta(hours=rental_hours)).strftime("%Y-%m-%d %H:%M:%S")
                            
                            c.execute("INSERT INTO RESERVATION (CUNY_ID, Vehicle_ID, Exp_Return, Act_Return) VALUES (?, ?, ?, NULL)", (cuny_id, veh_id, exp_return_time))
                            c.execute("UPDATE VEHICLE SET Status = 'Checked Out', Parked_Hub_ID = NULL WHERE Vehicle_ID = ?", (veh_id,))
                            conn.commit()
                            
                            st.success(f"Trip Started! Vehicle {veh_id} is due back exactly at {exp_return_time}.")

    # === TAB 2: RETURN ===
    with tab_in:
        st.subheader("Process a Return")
        st.write("Stamps the current time and clears the vehicle from the Overdue list if applicable.")
        
        # Show all active trips
        query = '''
            SELECT r.Reservation_ID, m.Full_Name, v.Vehicle_ID, v.Make, r.Exp_Return
            FROM RESERVATION r
            JOIN MEMBER m ON r.CUNY_ID = m.CUNY_ID
            JOIN VEHICLE v ON r.Vehicle_ID = v.Vehicle_ID
            WHERE r.Act_Return IS NULL
        '''
        df_active = pd.read_sql_query(query, conn)
        
        if df_active.empty:
            st.info("All vehicles are currently at their hubs. No active trips to return.")
        else:
            st.dataframe(df_active, use_container_width=True)
            
            with st.form("return_form"):
                res_id = st.number_input("Enter Reservation ID to Return", min_value=1, step=1)
                hub_return = st.number_input("Parked at Hub # (1-4)", min_value=1, max_value=4, step=1)
                
                if st.form_submit_button("Confirm Return"):
                    # Stamping CURRENT_TIMESTAMP handles the time processing automatically
                    c.execute("UPDATE RESERVATION SET Act_Return = CURRENT_TIMESTAMP WHERE Reservation_ID = ?", (res_id,))
                    
                    c.execute("SELECT Vehicle_ID FROM RESERVATION WHERE Reservation_ID = ?", (res_id,))
                    veh_row = c.fetchone()
                    if veh_row:
                        veh_id = veh_row[0]
                        c.execute("UPDATE VEHICLE SET Status = 'Available', Parked_Hub_ID = ? WHERE Vehicle_ID = ?", (hub_return, veh_id))
                    
                    conn.commit()
                    st.success(f"Return Processed! The live time was stamped and Vehicle {veh_id} is back in the Available pool.")

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
