
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
# TABLE LEAVE REQUESTS
# ======================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    leave_type TEXT,
    from_date TEXT,
    from_time TEXT,
    to_date TEXT,
    to_time TEXT,
    reason TEXT,
    status TEXT DEFAULT 'PENDING',
    is_read INTEGER DEFAULT 0,
    admin_note TEXT,
    created_at TEXT
)
""")
conn.commit()



# ======================================================
# TABLE NOTIFICATIONS
# ======================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    message TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT
)
""")
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

    'MatKhauMoi2026',

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

        attendance.late_reason AS 'Lý Do Đi Trễ',

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

if "role" not in st.session_state:
    st.session_state.role = ""

if "username" not in st.session_state:
    st.session_state.username = ""

if "employee_id" not in st.session_state:
    st.session_state.employee_id = ""

if "goto_menu" not in st.session_state:
    st.session_state.goto_menu = None

if "selected_leave_id" not in st.session_state:
    st.session_state.selected_leave_id = None

if "show_bell" not in st.session_state:
    st.session_state.show_bell = False

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
    f"{st.session_state.get('username','')}"
)

st.sidebar.write(
    f"🔐 Quyền: "
    f"{st.session_state.get('role','')}"
)


if st.sidebar.button("Đăng xuất"):

    st.session_state.clear()

    st.rerun()
# ==========================
# ==========================
# THÔNG BÁO
# ==========================

if st.session_state.role == "admin":

    unread_count = pd.read_sql_query(
        """
        SELECT COUNT(*) total
        FROM leave_requests
        WHERE status='PENDING'
        """,
        conn
    )["total"][0]

else:

    unread_count = pd.read_sql_query(
        """
        SELECT COUNT(*) total
        FROM notifications
        WHERE employee_id = ?
        AND is_read = 0
        """,
        conn,
        params=(st.session_state.employee_id,)
    )["total"][0]

# show_notice = st.sidebar.button(
#     f"🔔 Thông Báo ({unread_count})",
#     use_container_width=True
# )

# if show_notice:

#     if st.session_state.role == "admin":
#         menu = "Duyệt Đơn"
#     else:
#         menu = "Thông Báo"

# if show_notice:
#     st.session_state.show_notice = True
# ======================================================
# MENU
# ======================================================
if st.session_state.role == "admin":

    menu = st.sidebar.selectbox(
        "MENU",
        [

            "Dashboard",

            "Chấm Công",

            "Đơn Xin Phép",

            "Quản Lý Công",

            "Quản Lý Nhân Viên",

            "Tạo Tài Khoản",

            "Duyệt Đơn",

            "Thiết Lập Giờ",

            f"🔔 Thông Báo ({unread_count})"
        ]
    )

else:

    menu = st.sidebar.selectbox(
        "MENU",
        [

            "Dashboard",

            "Chấm Công",

            "Đơn Xin Phép",
            "Thông Báo"
        ]
    )
# if st.sidebar.button(
#     f"🔔 Thông Báo ({unread_count})"
# ):

#     st.session_state.goto_menu = "Thông Báo"

#     st.rerun()

# if st.session_state.goto_menu is not None:

#     menu = st.session_state.goto_menu

#     st.session_state.goto_menu = None
if st.session_state.goto_menu is not None:
    menu = st.session_state.goto_menu
    st.session_state.goto_menu = None

# st.sidebar.write(
#     "DEBUG MENU =",
#     menu
# )
# ======================================================
# DASHBOARD
# ======================================================
if menu == "Dashboard":

    top1, top2 = st.columns([9,1])

    with top2:

        if st.button(
            f"🔔 {unread_count}",
            key="top_bell"
        ):

            if st.session_state.role == "admin":

                if unread_count > 0:
                    st.session_state.goto_menu = "Duyệt Đơn"

                else:
                    st.session_state.goto_menu = (
                        f"🔔 Thông Báo ({unread_count})"
                    )

        else:

            st.session_state.goto_menu = "Thông Báo"

        st.rerun()

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

            # if not check_company_network():

            #     st.error(
            #         "❌ Không dùng wifi công ty."
            #     )

            # else:

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




# ======================================================
# THONG BAO
# ======================================================
elif menu.startswith("🔔 Thông Báo"):

    st.title("🔔 THÔNG BÁO")

    if st.session_state.role == "admin":

        pending = pd.read_sql_query(
            """
            SELECT COUNT(*) total
            FROM leave_requests
            WHERE status='PENDING'
            """,
            conn
        )["total"][0]

        if pending > 0:
            st.warning(
                f"📌 Có {pending} đơn xin phép cần duyệt."
            )

            if st.button("📂 MỞ DUYỆT ĐƠN"):

                st.session_state.goto_menu = "Duyệt Đơn"

                st.rerun()

        else:
            st.success("Không có đơn nào cần duyệt.")

    else:

        today = datetime.now().strftime("%Y-%m-%d")

        check_df = pd.read_sql_query(
            """
            SELECT COUNT(*) total
            FROM attendance
            WHERE employee_id=?
            AND date=?
            """,
            conn,
            params=(
                st.session_state.employee_id,
                today
            )
        )

        if check_df["total"][0] == 0:
            st.warning(
                "📌 Bạn chưa chấm công hôm nay."
            )

            if st.button("🕒 MỞ CHẤM CÔNG"):

                st.session_state.goto_menu = "Chấm Công"

                st.rerun()

        df_notice = pd.read_sql_query(
            """
            SELECT message,created_at
            FROM notifications
            WHERE employee_id=?
            ORDER BY id DESC
            """,
            conn,
            params=(st.session_state.employee_id,)
        )

        if not df_notice.empty:
            st.dataframe(
                df_notice,
                use_container_width=True
            )

# ======================================================
# DON XIN PHEP
# ======================================================
elif menu == "Đơn Xin Phép":
    st.title("📄 ĐƠN XIN PHÉP")

    loai = st.selectbox("Loại đơn",
        ["Nghỉ Phép","Đi Trễ","Về Sớm","Công Tác"])

    tu_ngay = st.date_input("Từ ngày")
    den_ngay = st.date_input("Đến ngày")

    ly_do = st.text_area("Lý do")

    if st.button("📤 Gửi Đơn"):
        cursor.execute("""
        INSERT INTO leave_requests(
            employee_id,leave_type,from_date,to_date,
            reason,status,created_at
        )
        VALUES(?,?,?,?,?,'PENDING',?)
        """,(
            st.session_state.employee_id,
            loai,
            str(tu_ngay),
            str(den_ngay),
            ly_do,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        st.success("Đã gửi đơn")

    # =========================
    # ĐƠN CHỜ DUYỆT
    # =========================
    st.subheader("🔵 ĐƠN CHỜ DUYỆT")

    df_pending = pd.read_sql_query(
        """
        SELECT *
        FROM leave_requests
        WHERE status='PENDING'
        ORDER BY id DESC
        """,
        conn
    )

    st.dataframe(
        df_pending,
        use_container_width=True
    )

    st.markdown("---")

# =========================
# ĐƠN ĐÃ DUYỆT
# =========================
    st.subheader("🟢 ĐƠN ĐÃ DUYỆT")

    df_approved = pd.read_sql_query(
        """
        SELECT *
        FROM leave_requests
        WHERE status='APPROVED'
        ORDER BY id DESC
        """,
        conn
    )

    st.dataframe(
        df_approved,
        use_container_width=True
    )

    st.markdown("---")

    # =========================
    # ĐƠN TỪ CHỐI
    # =========================
    st.subheader("🔴 ĐƠN ĐÃ TỪ CHỐI")

    df_rejected = pd.read_sql_query(
        """
        SELECT *
        FROM leave_requests
        WHERE status='REJECTED'
        ORDER BY id DESC
        """,
        conn
    )

    st.dataframe(
        df_rejected,
        use_container_width=True
    )

    st.markdown("---")
    # st.dataframe(df,use_container_width=True)

# ======================================================
# DUYET DON
# ======================================================
elif menu == "Duyệt Đơn":
    st.title("✅ DUYỆT ĐƠN")
    st.subheader("🔵 ĐƠN CHỜ DUYỆT")

    df_pending = pd.read_sql_query(
        """
        SELECT *
        FROM leave_requests
        WHERE status='PENDING'
        ORDER BY id DESC
        """,
        conn
    )

    st.dataframe(df_pending, use_container_width=True)

    st.markdown("---")

    st.subheader("🟢 ĐƠN ĐÃ DUYỆT")

    df_approved = pd.read_sql_query(
        """
        SELECT *
        FROM leave_requests
        WHERE status='APPROVED'
        ORDER BY id DESC
        """,
        conn
    )

    st.dataframe(df_approved, use_container_width=True)

    st.markdown("---")

    st.subheader("🔴 ĐƠN ĐÃ TỪ CHỐI")

    df_rejected = pd.read_sql_query(
        """
        SELECT *
        FROM leave_requests
        WHERE status='REJECTED'
        ORDER BY id DESC
        """,
        conn
    )

    for _, row in df_pending.iterrows():
 
        col1, col2, col3, col4, col5 = st.columns([1,2,2,2,1])

        col1.write(row["id"])
        col2.write(row["employee_id"])
        col3.write(row["leave_type"])
        col4.write(row["from_date"])

        if col5.button(
            "👁️",
            key=f"view_{row['id']}"
        ):
            st.session_state.selected_leave_id = row["id"]
    if st.session_state.selected_leave_id is not None:

        st.markdown("---")

        st.subheader("📄 CHI TIẾT ĐƠN")

        cursor.execute(
            """
            SELECT *
            FROM leave_requests
            WHERE id=?
            """,
            (
                st.session_state.selected_leave_id,
            )
        )

        detail = None

        if detail:

            st.write(f"**Nhân viên:** {detail[1]}")
            st.write(f"**Loại đơn:** {detail[2]}")
            st.write(f"**Từ ngày:** {detail[3]}")
            st.write(f"**Đến ngày:** {detail[5]}")
            st.write(f"**Lý do:** {detail[7]}")
                

        c1, c2 = st.columns(2)

        with c1:

            if st.button(
                "✅ DUYỆT",
                key="approve_btn"
            ):

                cursor.execute(
                    """
                    UPDATE leave_requests
                    SET status='APPROVED'
                    WHERE id=?
                    """,
                    (
                        st.session_state.selected_leave_id,
                    )
                )

                conn.commit()

                st.session_state.selected_leave_id = None

                st.rerun()

        with c2:

            if st.button(
                "❌ TỪ CHỐI",
                key="reject_btn"
            ):

                cursor.execute(
                    """
                    UPDATE leave_requests
                    SET status='REJECTED'
                    WHERE id=?
                    """,
                    (
                        st.session_state.selected_leave_id,
                    )
                )

                conn.commit()

                st.session_state.selected_leave_id = None

                st.rerun()   

 
