import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
import base64
from datetime import datetime, timedelta

# -------------------- USER MANAGEMENT --------------------
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Always ensure admin user exists with correct credentials and role
if 'users' not in st.session_state or 'admin' not in st.session_state['users']:
    st.session_state['users'] = {
        'admin': {
            'password': hash_password('admin123'),
            'role': 'admin'
        }
    }
else:
    # If users dict exists but admin is missing, add admin
    if 'admin' not in st.session_state['users']:
        st.session_state['users']['admin'] = {
            'password': hash_password('admin123'),
            'role': 'admin'
        }
    # If admin exists but password/role is wrong, reset them
    else:
        st.session_state['users']['admin']['password'] = hash_password('admin123')
        st.session_state['users']['admin']['role'] = 'admin'

def check_login(username, password):
    users = st.session_state['users']
    if username in users and users[username]['password'] == hash_password(password):
        return users[username]['role']
    return None

def add_user(username, password, role):
    st.session_state['users'][username] = {
        'password': hash_password(password),
        'role': role
    }

def remove_user(username):
    if username in st.session_state['users']:
        del st.session_state['users'][username]

def change_role(username, role):
    if username in st.session_state['users']:
        st.session_state['users'][username]['role'] = role

# -------------------- FILE UPLOADS --------------------
def load_file(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file, encoding='utf-8', engine='python')
        else:
            return pd.read_excel(uploaded_file, engine='openpyxl')
    except Exception:
        uploaded_file.seek(0)
        try:
            return pd.read_csv(uploaded_file, encoding='latin1', engine='python')
        except Exception:
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, engine='openpyxl')

def get_unique(df, col):
    if df is not None and col in df.columns:
        return df[col].dropna().unique().tolist()
    return []

# -------------------- SESSION STATE INIT --------------------
for key in ['master_df', 'device_df', 'disconnected_df']:
    if key not in st.session_state:
        st.session_state[key] = None

# -------------------- SIDEBAR NAVIGATION --------------------
st.set_page_config(page_title="Operations Dashboard", layout="wide")
st.sidebar.title("Navigation")

# Only show Admin Panel in sidebar if user is admin
if 'role' in st.session_state and st.session_state['role'] == 'admin':
    nav = st.sidebar.radio("Go to", ["User Dashboard", "Admin Panel"])
else:
    nav = "User Dashboard"

logout_btn = st.sidebar.button("Logout", key="logout_btn")

if logout_btn:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None
    st.rerun()

# -------------------- LOGIN PAGE --------------------
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.title("Login")
    tab1, tab2 = st.tabs(["Admin", "User"])
    with tab1:
        username = st.text_input("Admin Username", key="admin_user")
        password = st.text_input("Admin Password", type="password", key="admin_pass")
        if st.button("Login as Admin"):
            role = check_login(username, password)
            if role == 'admin':
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['role'] = role
                st.success("Logged in as Admin")
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        username = st.text_input("User Username", key="user_user")
        password = st.text_input("User Password", type="password", key="user_pass")
        if st.button("Login as User"):
            role = check_login(username, password)
            if role == 'user':
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['role'] = role
                st.success("Logged in as User")
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# -------------------- ADMIN PANEL --------------------
if nav == "Admin Panel":
    if st.session_state['role'] != 'admin':
        st.error("Access denied. Only admins can access this page.")
        st.stop()

    st.header("Admin Panel")
    st.subheader("Upload Files")
    col1, col2, col3 = st.columns(3)
    with col1:
        master_file = st.file_uploader("Upload Master File", type=['csv', 'xlsx'], key="master_file")
        if master_file:
            st.session_state['master_df'] = load_file(master_file)
            st.success("Master file uploaded")
    with col2:
        device_file = st.file_uploader("Upload Device Inventory", type=['csv', 'xlsx'], key="device_file")
        if device_file:
            st.session_state['device_df'] = load_file(device_file)
            st.success("Device Inventory uploaded")
    with col3:
        disconnected_file = st.file_uploader("Upload Disconnected Device Output File", type=['csv', 'xlsx'], key="disconnected_file")
        if disconnected_file:
            st.session_state['disconnected_df'] = load_file(disconnected_file)
            st.success("Disconnected Device Output File uploaded")

    st.divider()
    st.subheader("User Management")
    users = st.session_state['users']
    user_df = pd.DataFrame([
        {
            "Username": u,
            "Role": users[u]['role'],
            "Password": users[u]['password'] if st.session_state['role'] == 'admin' else "******"
        }
        for u in users
    ])
    st.dataframe(user_df, use_container_width=True)

    st.markdown("**Add User**")
    new_user = st.text_input("New Username")
    new_pass = st.text_input("New Password", type="password")
    new_role = st.selectbox("Role", ["user", "admin"])
    if st.button("Add User"):
        if new_user in users:
            st.warning("User already exists")
        else:
            add_user(new_user, new_pass, new_role)
            st.success("User added")
            st.rerun()

    st.markdown("**Remove User**")
    del_user = st.selectbox("Select User to Remove", [u for u in users if u != 'admin'])
    if st.button("Remove User"):
        remove_user(del_user)
        st.success("User removed")
        st.rerun()

    st.markdown("**Change Role**")
    ch_user = st.selectbox("Select User to Change Role", [u for u in users if u != 'admin'])
    ch_role = st.selectbox("New Role", ["user", "admin"], key="change_role")
    if st.button("Change Role"):
        change_role(ch_user, ch_role)
        st.success("Role changed")
        st.rerun()

    st.stop()

# -------------------- DATA VALIDATION --------------------
master_df = st.session_state['master_df']
device_df = st.session_state['device_df']
disconnected_df = st.session_state['disconnected_df']

if master_df is None or device_df is None or disconnected_df is None:
    st.warning("Please upload all required files in the Admin Panel.")
    st.stop()



# -------------------- FILTERS --------------------
# Prepare filter options
disconnected_df['entry_date'] = pd.to_datetime(disconnected_df['entry_date'], errors='coerce').dt.normalize()

max_date = disconnected_df['entry_date'].max()
date_list = sorted(disconnected_df['entry_date'].dropna().unique())
farm_status_list = ['All'] + get_unique(master_df, 'farm_status')
housing_type_list = ['All'] + get_unique(device_df, 'housing_type')
cluster_list = ['All'] + get_unique(master_df, 'Cluster')
farm_list = ['All'] + get_unique(master_df, 'farm_name')

# Top Row Filters
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_date = st.date_input("Select Date", value=max_date, min_value=min(date_list), max_value=max(date_list))
    with col2:
        selected_farm_status = st.selectbox("Farm Status", farm_status_list)
    with col3:
        selected_housing_type = st.selectbox("Housing Type", housing_type_list)

# Second Row Filters
with st.container():
    col4, col5 = st.columns(2)
    with col4:
        selected_cluster = st.selectbox("Select Cluster", cluster_list)
    with col5:
        selected_farm = st.selectbox("Select Farm", farm_list)

# Filter logic
def filter_data():
    df = disconnected_df.copy()
    dev_df = device_df.copy()
    mas_df = master_df.copy()


    # Farm Status
    if selected_farm_status != 'All':
        farms = mas_df[mas_df['farm_status'] == selected_farm_status]['farm_name'].unique()
        df = df[df['farm_name'].isin(farms)]
        dev_df = dev_df[dev_df['farm_name'].isin(farms)]
        mas_df = mas_df[mas_df['farm_status'] == selected_farm_status]

    # Housing Type
    if selected_housing_type != 'All':
        farms = dev_df[dev_df['housing_type'] == selected_housing_type]['farm_name'].unique()
        df = df[df['farm_name'].isin(farms)]
        dev_df = dev_df[dev_df['housing_type'] == selected_housing_type]
        mas_df = mas_df[mas_df['farm_name'].isin(farms)]

    # Cluster
    if selected_cluster != 'All':
        farms = mas_df[mas_df['Cluster'] == selected_cluster]['farm_name'].unique()
        df = df[df['farm_name'].isin(farms)]
        dev_df = dev_df[dev_df['farm_name'].isin(farms)]
        mas_df = mas_df[mas_df['Cluster'] == selected_cluster]

    # Farm
    if selected_farm != 'All':
        df = df[df['farm_name'] == selected_farm]
        dev_df = dev_df[dev_df['farm_name'] == selected_farm]
        mas_df = mas_df[mas_df['farm_name'] == selected_farm]

    return df, dev_df, mas_df

filtered_df, filtered_device_df, filtered_master_df = filter_data()

# -------------------- FARM INFORMATION CARDS --------------------
with st.container():
    st.markdown("### Total Devices")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        farm_count = filtered_master_df['farm_name'].nunique()
        st.metric("Farm Count", farm_count)
    with col2:
        if selected_farm == 'All' or filtered_master_df['farm_name'].nunique() != 1:
            farm_name = "All"
        else:
            farm_name = filtered_master_df['farm_name'].iloc[0]
        st.metric("Farm Name", farm_name)
    with col3:
        if selected_cluster == 'All' or filtered_master_df['Cluster'].nunique() != 1:
            cluster = "All"
        else:
            cluster = filtered_master_df['Cluster'].iloc[0]
        st.metric("Cluster", cluster)
    with col4:
        if filtered_master_df['vcm_name'].nunique() != 1:
            vcm_name = "All"
        else:
            vcm_name = filtered_master_df['vcm_name'].iloc[0]
        st.metric("VCM Name", vcm_name)

# -------------------- TOTAL DEVICE STATISTICS --------------------
with st.container():
    st.markdown("### Total Device Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        total_devices = filtered_df['deviceid'].nunique()
        st.metric("Total Devices", total_devices)
    with col2:
        b_type_devices = filtered_df[filtered_df['Device_type'] == 'B Type']['deviceid'].nunique()
        st.metric("B Type Devices", b_type_devices)
    with col3:
        c_type_devices = filtered_df[filtered_df['Device_type'] == 'C Type']['deviceid'].nunique()
        st.metric("C Type Devices", c_type_devices)

# -------------------- DISCONNECTED DEVICES STATISTICS --------------------
with st.container():
    st.markdown("### Disconnected Devices")
    col1, col2, col3 = st.columns(3)
    with col1:
        disconnected_devices = filtered_df[filtered_df['data_quality'] == 'Disconnected']['deviceid'].nunique()
        st.metric("Disconnected Devices", disconnected_devices)
    with col2:
        disconnected_b = filtered_df[(filtered_df['Device_type'] == 'B Type') & (filtered_df['data_quality'] == 'Disconnected')]['deviceid'].nunique()
        st.metric("Disconnected B", disconnected_b)
    with col3:
        disconnected_c = filtered_df[(filtered_df['Device_type'] == 'C Type') & (filtered_df['data_quality'] == 'Disconnected')]['deviceid'].nunique()
        st.metric("Disconnected C", disconnected_c)

# -------------------- GATEWAY STATISTICS --------------------
with st.container():
    st.markdown("### Gateway Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        # Gateway count should NOT be filtered by date, only by other dashboard filters
        gateway_count = device_df[
            (device_df['farm_name'].isin(filtered_device_df['farm_name'].unique())) &
            (device_df['housing_type'].isin(filtered_device_df['housing_type'].unique()))
        ]['gatewayid'].nunique()
        st.metric("Gateway Count", gateway_count)

with col2:
    gateway_ids = filtered_device_df['gatewayid'].unique()
    gateway_issue = "No"
    gateway_yes_count = 0
    for farm in filtered_device_df['farm_name'].unique():
        # All devices for this farm (from filtered_device_df)
        farm_devices = filtered_device_df[filtered_device_df['farm_name'] == farm]['deviceid'].unique()
        # Disconnected devices for this farm (from filtered_df, which is already filtered by date)
        disconnected_devices = filtered_df[
            (filtered_df['farm_name'] == farm) & 
            (filtered_df['data_quality'] == 'Disconnected')
        ]['deviceid'].unique()
        if len(farm_devices) > 0 and len(farm_devices) == len(disconnected_devices):
            gateway_issue = "Yes"
            gateway_yes_count += 1
    # Show count of Yes in the bracket after Yes
    if gateway_issue == "Yes":
        gateway_issue_display = f"Yes ({gateway_yes_count})"
    else:
        gateway_issue_display = "No"
    color = "red" if gateway_issue == "Yes" else "black"

    # Display up to 10 gateway IDs in a scrollable box
    gateway_ids_list = list(map(str, gateway_ids))
    gateway_ids_display = gateway_ids_list[:10]
    st.markdown(
        f"""
        <style>
        .scroll-box {{
            max-height:120px;
            overflow-y:scroll !important;
            border:1px solid #ccc;
            padding:8px;
            border-radius:4px;
        }}
        </style>
        <div class="scroll-box">
            <b>Gateway IDs:</b><br>
            {'<br>'.join(gateway_ids_display)}
        </div>
        """,
        unsafe_allow_html=True
    )
    with col3:
        st.metric("Gateway Issue", gateway_issue_display)

# -------------------- BREED STATISTICS --------------------
with st.container():
    st.markdown("### Breed Count")
    breed_counts = filtered_device_df['breed'].value_counts()
    st.dataframe(breed_counts.reset_index().rename(columns={'index': 'Breed', 'breed': 'Count'}))

# -------------------- DISCONNECTED DEVICES LIST --------------------
with st.container():
    st.markdown("### List of Disconnected Devices")
    disc_list = filtered_df[filtered_df['data_quality'] == 'Disconnected'][['deviceid', 'tag_number']]
    st.dataframe(disc_list.reset_index(drop=True))


# -------------------- DISCONNECTED DEVICES GRAPH --------------------
with st.container():
    st.markdown("### Disconnected Devices in Selected Duration")
    duration_map = {
        "7 days": 7,
        "1 Month": 30,
        "3 Month": 90,
        "6 Month": 180
    }
    col1, col2 = st.columns(2)
    with col1:
        duration = st.selectbox("Duration", list(duration_map.keys()), index=0)
    with col2:
        device_type_filter = st.selectbox("Device Type", ["All", "B Type", "C Type"], index=0)
    selected_date = pd.to_datetime(selected_date).normalize()
    end_date = selected_date
    start_date = end_date - timedelta(days=duration_map[duration] - 1)
    graph_df = filtered_df[
        (filtered_df['entry_date'] >= start_date) &
        (filtered_df['entry_date'] <= end_date)
    ]
    if device_type_filter != "All":
        graph_df = graph_df[graph_df['Device_type'] == device_type_filter]
    graph_df = graph_df[graph_df['data_quality'] == 'Disconnected']

    # Ensure all dates in range are present on X-axis
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    graph_data = graph_df.groupby('entry_date')['deviceid'].nunique().reindex(date_range, fill_value=0).reset_index()
    graph_data.columns = ['entry_date', 'deviceid']

    st.write("start_date:", start_date)
    st.write("end_date:", end_date)
    st.write("Graph Data Preview:", graph_data)

    if not graph_data.empty:
        fig = px.bar(
            graph_data,
            x='entry_date',
            y='deviceid',
            labels={'deviceid': 'Disconnected Devices', 'entry_date': 'Date'},
            title=f"Disconnected Devices in Previous {duration}"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No disconnected devices for the selected duration and filters.")

# -------------------- DISCONNECTED GATEWAY GRAPH --------------------
with st.container():
    st.markdown("### Disconnected Gateways Over Time")
    duration2 = st.selectbox("Gateway Duration", list(duration_map.keys()), index=0, key="gateway_duration")  # Default to 7 days
    end_date2 = pd.to_datetime(selected_date)
    start_date2 = end_date2 - timedelta(days=duration_map[duration2])

    gateway_graph_df = filtered_df[
        (filtered_df['entry_date'] >= start_date2) &
        (filtered_df['entry_date'] <= end_date2)
    ]
    gateway_device_df = filtered_device_df.copy()

    gateway_issue_data = []
    for date in sorted(gateway_graph_df['entry_date'].unique()):
        day_df = gateway_graph_df[gateway_graph_df['entry_date'] == date]
        farms = gateway_device_df['farm_name'].unique()
        count_yes = 0
        for farm in farms:
            farm_devices = gateway_device_df[gateway_device_df['farm_name'] == farm]['deviceid'].unique()
            disconnected_devices = day_df[
                (day_df['farm_name'] == farm) & 
                (day_df['data_quality'] == 'Disconnected')
            ]['deviceid'].unique()
            if len(farm_devices) > 0 and len(farm_devices) == len(disconnected_devices):
                count_yes += 1
        gateway_issue_data.append({'entry_date': date, 'gateway_issue': count_yes})

    gateway_graph_data = pd.DataFrame(gateway_issue_data)

    st.write("Graph Data Preview:", graph_data)

    if not gateway_graph_data.empty:
        fig2 = px.bar(
            gateway_graph_data,
            x='entry_date',
            y='gateway_issue',
            labels={'gateway_issue': 'Count of Gateway Issues (Yes)'},
            title="Disconnected Gateways Over Time"
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data available for the selected duration and filters.")