
# ======================================================
# IMPORT
# ======================================================
import os
import time
import socket
import sqlite3

from datetime import datetime

import pandas as pd
import streamlit as st

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Hệ Thống Chấm Công",
    page_icon="🕒",
    layout="wide"
)

# ======================================================
# DATABASE
# ======================================================
DB_NAME = "attendance.db"

conn = sqlite3.connect(
    DB_NAME,
    check_same_thread=False
)

cursor = conn.cursor()

# ======================================================
# RESET DATABASE KHI TEST
# ======================================================
# XÓA COMMENT NẾU MUỐN RESET DB
#
# os.remove("attendance.db")

# ======================================================
# TABLE USERS
# ======================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (

    username TEXT PRIMARY KEY,

    password TEXT,

    role TEXT,

    employee_id TEXT
)
""")

# ======================================================
# TABLE EMPLOYEES
# ======================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (

    id TEXT PRIMARY KEY,

    name TEXT,

    department TEXT
)
""")

# ======================================================
# TABLE ATTENDANCE
# ======================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    employee_id TEXT,

    date TEXT,

    checkin TEXT,

    checkout TEXT,

    status TEXT,

    work_day REAL
)
""")

# ======================================================
# TABLE SETTINGS
# ======================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (

    id INTEGER PRIMARY KEY,

    start_time TEXT,

    grace_time INTEGER,

    lunch_out TEXT,

    lunch_in TEXT,

    end_time TEXT
)
""")


conn.commit()

for col_sql in [
    "ALTER TABLE attendance ADD COLUMN early_leave_reason TEXT",
    "ALTER TABLE attendance ADD COLUMN late_reason TEXT"
]:
    try:
        cursor.execute(col_sql)
    except:
        pass

conn.commit()

# ======================================================
# SETTINGS DEFAULT
# ======================================================
cursor.execute("""
SELECT *
FROM settings
WHERE id = 1
""")

settings_exist = cursor.fetchone()

if not settings_exist:

    cursor.execute("""
    INSERT INTO settings (

        id,

        start_time,

        grace_time,

        lunch_out,

        lunch_in,

        end_time

    )

    VALUES (?, ?, ?, ?, ?, ?)
    """, (

        1,

        "08:00:00",

        15,

        "12:00:00",

        "13:00:00",

        "17:00:00"
    ))

    conn.commit()

# ======================================================
# ADMIN DEFAULT
# ======================================================
cursor.execute("""
INSERT OR IGNORE INTO users
VALUES (

    'admin',

    '123',

    'admin',

    'ADMIN'
)
""")

conn.commit()

# ======================================================
# LOGIN
# ======================================================
def login(username, password):

    cursor.execute("""
    SELECT *
    FROM users

    WHERE username = ?
    AND password = ?
    """, (

        username,

        password
    ))

    return cursor.fetchone()

# ======================================================
# GET EMPLOYEE
# ======================================================
def get_employee(emp_id):

    cursor.execute("""
    SELECT *
    FROM employees

    WHERE id = ?
    """, (emp_id,))

    return cursor.fetchone()

# ======================================================
# GET SETTINGS
# ======================================================
def get_settings():

    cursor.execute("""
    SELECT *
    FROM settings

    WHERE id = 1
    """)

    data = cursor.fetchone()

    # ==============================================
    # FIX DATABASE CŨ
    # ==============================================
    if len(data) < 6:

        cursor.execute("""
        DROP TABLE settings
        """)

        conn.commit()

        cursor.execute("""
        CREATE TABLE settings (

            id INTEGER PRIMARY KEY,

            start_time TEXT,

            grace_time INTEGER,

            lunch_out TEXT,

            lunch_in TEXT,

            end_time TEXT
        )
        """)

        conn.commit()

        cursor.execute("""
        INSERT INTO settings
        VALUES (?, ?, ?, ?, ?, ?)
        """, (

            1,

            "08:00:00",

            15,

            "12:00:00",

            "13:00:00",

            "17:00:00"
        ))

        conn.commit()

        cursor.execute("""
        SELECT *
        FROM settings
        WHERE id = 1
        """)

        data = cursor.fetchone()

    return data

# ======================================================
# CHECK WIFI CÔNG TY
# ======================================================
def check_company_network():

    hostname = socket.gethostname()

    local_ip = socket.gethostbyname(
        hostname
    )

    allowed_network = "10.10.10."

    if local_ip.startswith(
        allowed_network
    ):

        return True

    return False

# ======================================================
# CALCULATE STATUS
# ======================================================
def calculate_status(checkin_time):

    settings = get_settings()

    office_time = settings[1]

    try:

        grace_minutes = int(
            settings[2]
        )

    except:

        grace_minutes = 15

    office_dt = datetime.strptime(
        office_time,
        "%H:%M:%S"
    )

    checkin_dt = datetime.strptime(
        checkin_time,
        "%H:%M:%S"
    )

    diff_minutes = (
        checkin_dt - office_dt
    ).total_seconds() / 60

    # ==============================================
    # ĐÚNG GIỜ
    # ==============================================
    if diff_minutes <= grace_minutes:

        return (
            "🟢 Đúng Giờ",
            1
        )

    # ==============================================
    # ĐI TRỄ
    # ==============================================
    return (
        "🟡 Đi Trễ",
        0.5
    )

# ======================================================
# CHECK IN
# ======================================================
def check_in(emp_id):

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    now = datetime.now().strftime(
        "%H:%M:%S"
    )

    cursor.execute("""
    SELECT *
    FROM attendance

    WHERE employee_id = ?
    AND date = ?
    """, (

        emp_id,

        today
    ))

    existing = cursor.fetchone()

    if existing:

        return (
            False,
            "⚠️ Hôm nay đã check in."
        )

    status, work_day = calculate_status(
        now
    )

    cursor.execute("""
    INSERT INTO attendance (

        employee_id,

        date,

        checkin,

        checkout,

        status,

        work_day
    )

    VALUES (?, ?, ?, ?, ?, ?)
    """, (

        emp_id,

        today,

        now,

        "",

        status,

        work_day
    ))

    conn.commit()

    return (
        True,
        f"✅ Check in thành công lúc {now}"
    )

# ======================================================
# CHECK OUT
# ======================================================
def check_out(emp_id, reason=''):

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    now = datetime.now().strftime(
        "%H:%M:%S"
    )

    cursor.execute("""
    SELECT *
    FROM attendance

    WHERE employee_id = ?
    AND date = ?
    """, (

        emp_id,

        today
    ))

    existing = cursor.fetchone()

    if not existing:

        return (
            False,
            "⚠️ Bạn chưa check in."
        )

    if existing[4] != "":

        return (
            False,
            "⚠️ Bạn đã check out."
        )

    cursor.execute("""
    UPDATE attendance

    SET
        checkout = ?,
        early_leave_reason = ?

    WHERE employee_id = ?
    AND date = ?
    """, (

        now,

        reason,

        emp_id,

        today
    ))

    conn.commit()

    return (
        True,
        f"✅ Check out thành công lúc {now}"
    )

# ======================================================
# LOAD ATTENDANCE
# ======================================================
def load_attendance():

    query = """
    SELECT

        attendance.employee_id AS 'Mã NV',

        employees.name AS 'Tên Nhân Viên',

        employees.department AS 'Phòng Ban',

        attendance.date AS 'Ngày',

        attendance.checkin AS 'Check In',

        attendance.checkout AS 'Check Out',

        attendance.status AS 'Trạng Thái',

        attendance.work_day AS 'Công',

        attendance.early_leave_reason AS 'Lý Do Về Sớm'

    FROM attendance

    LEFT JOIN employees
    ON attendance.employee_id = employees.id

    ORDER BY attendance.date DESC
    """

    return pd.read_sql_query(
        query,
        conn
    )

# ======================================================
# SESSION
# ======================================================
if "logged_in" not in st.session_state:

    st.session_state.logged_in = False

# ======================================================
# LOGIN PAGE
# ======================================================
if not st.session_state.logged_in:

    st.title(
        "🕒 ĐĂNG NHẬP HỆ THỐNG"
    )

    username = st.text_input(
        "Tên đăng nhập"
    )

    password = st.text_input(
        "Mật khẩu",
        type="password"
    )

    if st.button("ĐĂNG NHẬP"):

        user = login(
            username,
            password
        )

        if user:

            st.session_state.logged_in = True

            st.session_state.username = user[0]

            st.session_state.role = user[2]

            st.session_state.employee_id = user[3]

            st.success(
                "✅ Đăng nhập thành công"
            )

            time.sleep(1)

            st.rerun()

        else:

            st.error(
                "❌ Sai tài khoản hoặc mật khẩu."
            )

    st.stop()

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.title(
    "🕒 HỆ THỐNG CHẤM CÔNG"
)

st.sidebar.success(
    f"👋 Xin chào: "
    f"{st.session_state.username}"
)

st.sidebar.write(
    f"🔐 Quyền: "
    f"{st.session_state.role}"
)

if st.sidebar.button("Đăng xuất"):

    st.session_state.logged_in = False

    st.rerun()

# ======================================================
# MENU
# ======================================================
if st.session_state.role == "admin":

    menu = st.sidebar.selectbox(
        "MENU",
        [

            "Dashboard",

            "Chấm Công",

            "Quản Lý Công",

            "Quản Lý Nhân Viên",

            "Tạo Tài Khoản",

            "Thiết Lập Giờ"
        ]
    )

else:

    menu = st.sidebar.selectbox(
        "MENU",
        [

            "Dashboard",

            "Chấm Công"
        ]
    )

# ======================================================
# DASHBOARD
# ======================================================
if menu == "Dashboard":

    st.title("📊 DASHBOARD")

    total_emp = pd.read_sql_query(
        """
        SELECT COUNT(*) total
        FROM employees
        """,
        conn
    )["total"][0]

    late_count = pd.read_sql_query(
        """
        SELECT COUNT(*) total
        FROM attendance
        WHERE status LIKE '%Trễ%'
        """,
        conn
    )["total"][0]

    total_workday = pd.read_sql_query(
        """
        SELECT SUM(work_day) total
        FROM attendance
        """,
        conn
    )["total"][0]

    if total_workday is None:

        total_workday = 0

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "👨‍💼 Nhân Viên",
        total_emp
    )

    col2.metric(
        "🟡 Đi Trễ",
        late_count
    )

    col3.metric(
        "📅 Tổng Công",
        total_workday
    )

# ======================================================
# CHẤM CÔNG
# ======================================================
elif menu == "Chấm Công":

    st.title("🕒 CHẤM CÔNG")

    settings = get_settings()

    st.info(
        f"""
        ⏰ Giờ vào:
        {settings[1]}

        🟢 Cho phép trễ:
        {settings[2]} phút
        """
    )

    emp_id = st.session_state.employee_id

    emp = get_employee(emp_id)

    if emp:

        st.success(
            f"👤 {emp[1]} | 🏢 {emp[2]}"
        )

    late_reason = st.text_area(
        "📝 Lý do đi trễ (nếu có)"
    )

    reason = st.text_area(
        "📝 Lý do về sớm (nếu có)",
        placeholder="Nhập lý do nếu về trước giờ tan làm"
    )

    col1, col2 = st.columns(2)

    # ==============================================
    # CHECK IN
    # ==============================================
    with col1:

        if st.button(
            "✅ CHECK IN",
            use_container_width=True
        ):

            if not check_company_network():

                st.error(
                    "❌ Không dùng wifi công ty."
                )

            else:

                success, msg = check_in(
                    emp_id
                )

                if success:

                    st.success(msg)

                    st.balloons()

                else:

                    st.error(msg)

    # ==============================================
    # CHECK OUT
    # ==============================================
    with col2:

        if st.button(
            "❌ CHECK OUT",
            use_container_width=True
        ):

            if not check_company_network():

                st.error(
                    "❌ Không dùng wifi công ty."
                )

            else:

                success, msg = check_out(
                    emp_id,
                    reason
                )

                if success:

                    st.success(msg)

                    st.balloons()

                else:

                    st.error(msg)

# ======================================================
# QUẢN LÝ CÔNG
# ======================================================
elif menu == "Quản Lý Công":

    st.title("📋 QUẢN LÝ CHẤM CÔNG")

    df = load_attendance()

    if not df.empty:
        months = sorted(pd.to_datetime(df["Ngày"]).dt.strftime("%Y-%m").unique(), reverse=True)
        selected_month = st.selectbox("📅 Chọn tháng", months)

        employees_filter = ["Tất cả"] + sorted(df["Tên Nhân Viên"].fillna("").unique().tolist())
        selected_emp = st.selectbox("👤 Nhân viên", employees_filter)

        df = df[pd.to_datetime(df["Ngày"]).dt.strftime("%Y-%m") == selected_month]

        if selected_emp != "Tất cả":
            df = df[df["Tên Nhân Viên"] == selected_emp]

    st.dataframe(
        df,
        use_container_width=True
    )

    if not os.path.exists("exports"):

        os.makedirs("exports")

    if st.button("📥 EXPORT EXCEL"):

        filename = (
            f"exports/"
            f"attendance_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        df.to_excel(
            filename,
            index=False
        )

        st.success(
            f"✅ Đã xuất file: {filename}"
        )

        st.balloons()

# ======================================================
# QUẢN LÝ NHÂN VIÊN
# ======================================================
elif menu == "Quản Lý Nhân Viên":

    st.title("👨‍💼 QUẢN LÝ NHÂN VIÊN")

    emp_df = pd.read_sql_query(
        "SELECT * FROM employees",
        conn
    )

    st.dataframe(
        emp_df,
        use_container_width=True
    )

    st.markdown("---")

    st.subheader(
        "➕ THÊM NHÂN VIÊN"
    )

    emp_id = st.text_input(
        "Mã nhân viên"
    )

    emp_name = st.text_input(
        "Tên nhân viên"
    )

    emp_department = st.text_input(
        "Phòng ban"
    )

    if st.button("➕ THÊ M NHÂN VIÊN"):

        cursor.execute("""
        INSERT INTO employees
        VALUES (?, ?, ?)
        """, (

            emp_id,

            emp_name,

            emp_department
        ))

        conn.commit()

        st.success(
            "✅ Đã thêm nhân viên."
        )

# ======================================================
# TẠO TÀI KHOẢN
# ======================================================
elif menu == "Tạo Tài Khoản":

    st.title("🔐 TẠO TÀI KHOẢN")

    username = st.text_input(
        "Tên đăng nhập"
    )

    password = st.text_input(
        "Mật khẩu",
        type="password"
    )

    employees = pd.read_sql_query(
        "SELECT * FROM employees",
        conn
    )

    employee_options = {}

    for _, row in employees.iterrows():

        label = (
            f"{row['id']} - "
            f"{row['name']}"
        )

        employee_options[label] = row["id"]

    selected_emp = st.selectbox(
        "Chọn nhân viên",
        list(employee_options.keys())
    )

    role = st.selectbox(
        "Quyền",
        ["user", "admin"]
    )

    if st.button("➕ TẠO TÀI KHOẢN"):

        employee_id = employee_options[
            selected_emp
        ]

        cursor.execute("""
        INSERT INTO users
        VALUES (?, ?, ?, ?)
        """, (

            username,

            password,

            role,

            employee_id
        ))

        conn.commit()

        st.success(
            "✅ Đã tạo tài khoản."
        )

# ======================================================
# THIẾT LẬP GIỜ
# ======================================================
elif menu == "Thiết Lập Giờ":

    st.title("⏰ THIẾT LẬP GIỜ")

    settings = get_settings()

    start_time = st.text_input(
        "Giờ vào làm",
        value=settings[1]
    )

    # ==============================================
    # FIX INT
    # ==============================================
    grace_default = 15

    try:

        grace_default = int(
            settings[2]
        )

    except:

        pass

    grace_time = st.number_input(
        "Phút cho phép đi trễ",
        min_value=0,
        max_value=120,
        value=grace_default
    )

    lunch_out = st.text_input(
        "Giờ nghỉ trưa",
        value=settings[3]
    )

    lunch_in = st.text_input(
        "Giờ vào lại",
        value=settings[4]
    )

    end_time = st.text_input(
        "Giờ tan làm",
        value=settings[5]
    )

    st.info(
        f"""
        ⏰ Giờ vào:
        {start_time}

        🟢 Cho phép trễ:
        {grace_time} phút

        👉 Sau thời gian trên
        mới bị tính đi trễ.
        """
    )

    # ==============================================
    # SAVE SETTINGS
    # ==============================================
    if st.button("💾 LƯU THIẾT LẬP"):

        cursor.execute("""
        UPDATE settings

        SET
            start_time = ?,
            grace_time = ?,
            lunch_out = ?,
            lunch_in = ?,
            end_time = ?

        WHERE id = 1
        
        """, (

            start_time,

            int(grace_time),

            lunch_out,

            lunch_in,

            end_time
        ))

        conn.commit()

        st.success(
            "✅ Đã lưu thiết lập."
        )

        st.balloons()

