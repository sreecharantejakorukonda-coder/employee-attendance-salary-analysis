


import sqlite3
import calendar
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Employee Attendance & Salary Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "employee_system.db"

DEPARTMENTS = [
    "IT", "HR", "Finance", "Marketing", "Sales",
    "Operations", "Research"
]

STATUSES = [
    "Present", "Absent", "Half Day", "Work From Home",
    "Leave", "Holiday", "Weekly Off"
]

LEAVE_TYPES = [
    "Casual Leave", "Sick Leave", "Earned Leave",
    "Personal Leave", "Unpaid Leave"
]

# =========================================================
# DATABASE
# =========================================================
def connect():
    con = sqlite3.connect(DB_NAME, timeout=30)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT,
                designation TEXT,
                basic REAL DEFAULT 0,
                hra REAL DEFAULT 0,
                allowance REAL DEFAULT 0,
                active INTEGER DEFAULT 1
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                work_date TEXT NOT NULL,
                status TEXT NOT NULL,
                overtime REAL DEFAULT 0,
                UNIQUE(employee_id, work_date),
                FOREIGN KEY(employee_id)
                    REFERENCES employees(employee_id)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS leaves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                leave_type TEXT,
                days REAL DEFAULT 1,
                approval TEXT DEFAULT 'Pending',
                FOREIGN KEY(employee_id)
                    REFERENCES employees(employee_id)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS payroll (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                month TEXT NOT NULL,
                paid_days REAL DEFAULT 0,
                bonus REAL DEFAULT 0,
                deductions REAL DEFAULT 0,
                overtime_pay REAL DEFAULT 0,
                gross REAL DEFAULT 0,
                net REAL DEFAULT 0,
                payment_status TEXT DEFAULT 'Not Paid',
                payment_date TEXT,
                overtime_hours REAL DEFAULT 0,
                hourly_rate REAL DEFAULT 0,
                UNIQUE(employee_id, month),
                FOREIGN KEY(employee_id)
                    REFERENCES employees(employee_id)
            )
        """)

        # Safe migrations for older databases
        migrations = {
            "employees": {
                "highest_qualification": "TEXT DEFAULT ''",
                "specialization": "TEXT DEFAULT ''",
                "university": "TEXT DEFAULT ''",
                "graduation_year": "INTEGER",
                "experience_years": "REAL DEFAULT 0",
                "previous_company": "TEXT DEFAULT ''",
                "joining_date": "TEXT"
            },
            "payroll": {
                "payment_status": "TEXT DEFAULT 'Not Paid'",
                "payment_date": "TEXT",
                "overtime_hours": "REAL DEFAULT 0",
                "hourly_rate": "REAL DEFAULT 0"
            }
        }

        for table, columns in migrations.items():
            existing = {
                row[1]
                for row in con.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }

            for column, definition in columns.items():
                if column not in existing:
                    con.execute(
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN {column} {definition}"
                    )


def seed_demo_data():
    """Insert fictional demo employees only if the table is empty."""
    with connect() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM employees"
        ).fetchone()[0]

        if count:
            return

        demo_employees = [
            ("EMP001", "Ravi Kumar", "IT", "Python Developer",
             30000, 8000, 5000, "B.Tech", "Computer Science",
             "Example University", 2024, 2, "ABC Technologies"),
            ("EMP002", "Priya Sharma", "IT", "Data Analyst",
             35000, 9000, 6000, "M.Sc", "Data Analytics",
             "Example University", 2023, 3, "Demo Analytics"),
            ("EMP003", "Suresh Reddy", "HR", "HR Executive",
             25000, 6000, 4000, "MBA", "Human Resources",
             "Example Business School", 2022, 4, "Demo Services"),
            ("EMP004", "Anjali Devi", "HR", "HR Manager",
             40000, 10000, 7000, "MBA", "Human Resources",
             "Example Business School", 2020, 6, "Demo Group"),
            ("EMP005", "Kiran Kumar", "Finance", "Accountant",
             28000, 7000, 3000, "B.Com", "Accounting",
             "Example College", 2023, 3, "Demo Finance"),
            ("EMP006", "Sneha Rao", "Finance", "Finance Manager",
             45000, 12000, 8000, "M.Com", "Finance",
             "Example University", 2019, 7, "Demo Finance Group"),
            ("EMP007", "Arjun Varma", "Marketing", "Marketing Executive",
             26000, 6500, 4500, "BBA", "Marketing",
             "Example College", 2024, 2, "Demo Media"),
            ("EMP008", "Divya Reddy", "Marketing", "Marketing Manager",
             38000, 9500, 6000, "MBA", "Marketing",
             "Example Business School", 2021, 5, "Demo Media Group"),
            ("EMP009", "Manoj Kumar", "IT", "ML Engineer",
             42000, 11000, 7000, "M.Tech", "Artificial Intelligence",
             "Example University", 2022, 4, "Demo AI Labs"),
            ("EMP010", "Pooja Singh", "HR", "Recruiter",
             27000, 6500, 3500, "B.A.", "Psychology",
             "Example College", 2023, 3, "Demo Recruitment")
        ]

        for e in demo_employees:
            con.execute("""
                INSERT INTO employees (
                    employee_id, name, department, designation,
                    basic, hra, allowance, active,
                    highest_qualification, specialization,
                    university, graduation_year, experience_years,
                    previous_company, joining_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
            """, (
                *e,
                "2026-01-01"
            ))


init_db()
seed_demo_data()

# =========================================================
# DATA HELPERS
# =========================================================
def read_sql(query, params=()):
    with connect() as con:
        return pd.read_sql_query(query, con, params=params)


def execute_sql(query, params=()):
    with connect() as con:
        con.execute(query, params)


def employee_ids(active_only=False):
    sql = "SELECT employee_id, name FROM employees"
    if active_only:
        sql += " WHERE active=1"
    sql += " ORDER BY employee_id"
    df = read_sql(sql)
    return {
        f"{row.employee_id} — {row.name}": row.employee_id
        for row in df.itertuples()
    }


def money(value):
    return f"₹{float(value or 0):,.2f}"


def get_employee(emp_id):
    df = read_sql(
        "SELECT * FROM employees WHERE employee_id=?",
        (emp_id,)
    )
    return None if df.empty else df.iloc[0]


def get_month_attendance(emp_id, month):
    start = f"{month}-01"
    last_day = calendar.monthrange(
        int(month[:4]), int(month[5:7])
    )[1]
    end = f"{month}-{last_day:02d}"

    return read_sql("""
        SELECT work_date, status, overtime
        FROM attendance
        WHERE employee_id=?
          AND work_date BETWEEN ? AND ?
        ORDER BY work_date
    """, (emp_id, start, end))


def attendance_summary(df):
    if df.empty:
        return {
            "Present": 0, "Absent": 0, "Half Day": 0,
            "Work From Home": 0, "Leave": 0,
            "Holiday": 0, "Weekly Off": 0,
            "Present Equivalent": 0, "Paid Days": 0,
            "Overtime Hours": 0, "Attendance %": 0
        }

    counts = df["status"].value_counts().to_dict()
    present = counts.get("Present", 0)
    absent = counts.get("Absent", 0)
    half = counts.get("Half Day", 0)
    wfh = counts.get("Work From Home", 0)

    # Demo policy: Present/WFH = 1 day; Half Day = 0.5 day.
    # Leave, holidays, and weekly offs are excluded from paid days.
    equivalent = present + wfh + half * 0.5
    denominator = present + wfh + half + absent

    result = {
        status: counts.get(status, 0)
        for status in STATUSES
    }
    result["Present Equivalent"] = equivalent
    result["Paid Days"] = equivalent
    result["Overtime Hours"] = df["overtime"].fillna(0).sum()
    result["Attendance %"] = (
        100 * equivalent / denominator if denominator else 0
    )
    return result


def calculate_payroll(emp, month, paid_days, overtime_hours,
                      hourly_rate, bonus, deductions):
    days_in_month = calendar.monthrange(
        int(month[:4]), int(month[5:7])
    )[1]

    monthly_salary = (
        float(emp["basic"] or 0)
        + float(emp["hra"] or 0)
        + float(emp["allowance"] or 0)
    )

    paid_days = max(0, min(float(paid_days), days_in_month))
    overtime_hours = max(0, float(overtime_hours))
    hourly_rate = max(0, float(hourly_rate))
    bonus = max(0, float(bonus))
    deductions = max(0, float(deductions))

    base_pay = monthly_salary * paid_days / days_in_month
    overtime_pay = overtime_hours * hourly_rate
    gross = base_pay + overtime_pay + bonus
    net = max(0, gross - deductions)

    return {
        "monthly_salary": monthly_salary,
        "base_pay": base_pay,
        "overtime_hours": overtime_hours,
        "hourly_rate": hourly_rate,
        "overtime_pay": overtime_pay,
        "bonus": bonus,
        "deductions": deductions,
        "gross": gross,
        "net": net,
        "paid_days": paid_days
    }


# =========================================================
# STYLING
# =========================================================
st.markdown("""
<style>
    .stApp { background-color: #f5f7fb; }
    [data-testid="stSidebar"] {
        background-color: #102a43;
    }
    [data-testid="stSidebar"] * {
        color: white;
    }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e3eaf2;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,.04);
    }
    h1, h2, h3 { color: #16324f; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# NAVIGATION
# =========================================================
st.sidebar.title("🏢 HR Analytics")
st.sidebar.caption("Employee Management System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Employee Management",
        "Attendance",
        "Attendance Comparison",
        "Leave Management",
        "Salary & Payroll",
        "Department Comparison",
        "Monthly Reports",
        "Export Data"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Demo records are fictional.")
st.sidebar.caption("Database: employee_system.db")

# =========================================================
# DASHBOARD
# =========================================================
if page == "Dashboard":
    st.title("📊 Employee Attendance & Salary Dashboard")
    st.caption("Overview of employees, attendance and payroll")

    employees = read_sql("SELECT * FROM employees")
    attendance = read_sql("SELECT * FROM attendance")
    payroll = read_sql("SELECT * FROM payroll")

    active_count = (
        int(employees["active"].sum()) if not employees.empty else 0
    )
    latest_payroll = (
        payroll.groupby("month")["net"].sum()
        if not payroll.empty else pd.Series(dtype=float)
    )
    latest_month_total = (
        latest_payroll.iloc[-1] if not latest_payroll.empty else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Employees", len(employees))
    c2.metric("Active Employees", active_count)
    c3.metric("Attendance Records", len(attendance))
    c4.metric("Latest Payroll Total", money(latest_month_total))

    left, right = st.columns(2)

    with left:
        st.subheader("Employees by Department")
        if not employees.empty:
            dept = employees.groupby("department").size().reset_index(
                name="Employees"
            )
            st.plotly_chart(
                px.bar(dept, x="department", y="Employees",
                       color="department", title="Department Headcount"),
                use_container_width=True
            )

    with right:
        st.subheader("Attendance Status")
        if not attendance.empty:
            status_counts = attendance["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Records"]
            st.plotly_chart(
                px.pie(status_counts, names="Status", values="Records",
                       hole=0.45, title="All Recorded Attendance Statuses"),
                use_container_width=True
            )
        else:
            st.info("No attendance records yet.")

    st.subheader("Monthly Payroll")
    if not payroll.empty:
        monthly = payroll.groupby("month", as_index=False)["net"].sum()
        st.plotly_chart(
            px.line(monthly, x="month", y="net", markers=True,
                    title="Saved Net Payroll by Month"),
            use_container_width=True
        )
    else:
        st.info("Save payroll records to view this chart.")

    st.subheader("Attendance Status Counts")
    if not attendance.empty:
        status_counts = attendance.groupby("status").size().reset_index(
            name="Records"
        )
        st.dataframe(status_counts, use_container_width=True, hide_index=True)
        st.write(
            f"Total records: **{len(attendance)}**. "
            "The table includes every status present in the database."
        )

# =========================================================
# EMPLOYEE MANAGEMENT
# =========================================================
elif page == "Employee Management":
    st.title("👥 Employee Management")

    tab_add, tab_edit, tab_view = st.tabs(
        ["Add Employee", "Edit / Delete", "Employee Directory"]
    )

    with tab_add:
        st.subheader("Add New Employee")
        with st.form("add_employee_form"):
            c1, c2 = st.columns(2)
            emp_id = c1.text_input("Employee ID", placeholder="EMP011")
            name = c2.text_input("Full Name")
            department = c1.selectbox("Department", DEPARTMENTS)
            designation = c2.text_input("Designation")

            c1, c2, c3 = st.columns(3)
            basic = c1.number_input("Basic Salary (₹)", min_value=0.0)
            hra = c2.number_input("HRA (₹)", min_value=0.0)
            allowance = c3.number_input("Allowance (₹)", min_value=0.0)

            st.markdown("#### Education Details")
            c1, c2 = st.columns(2)
            qualification = c1.text_input("Highest Qualification")
            specialization = c2.text_input("Specialization")
            university = c1.text_input("University / College")
            graduation_year = c2.number_input(
                "Graduation Year", min_value=0, max_value=2100, value=0
            )

            st.markdown("#### Work Experience")
            c1, c2 = st.columns(2)
            experience = c1.number_input(
                "Experience (Years)", min_value=0.0, step=0.5
            )
            previous_company = c2.text_input("Previous Company")
            joining_date = st.date_input("Joining Date", value=date.today())

            submitted = st.form_submit_button(
                "Add Employee", use_container_width=True
            )

            if submitted:
                if not emp_id.strip() or not name.strip():
                    st.error("Employee ID and name are required.")
                else:
                    try:
                        execute_sql("""
                            INSERT INTO employees (
                                employee_id, name, department, designation,
                                basic, hra, allowance, active,
                                highest_qualification, specialization,
                                university, graduation_year, experience_years,
                                previous_company, joining_date
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            emp_id.strip(), name.strip(), department,
                            designation.strip(), basic, hra, allowance,
                            qualification, specialization, university,
                            graduation_year if graduation_year else None,
                            experience, previous_company,
                            joining_date.isoformat()
                        ))
                        st.success("Employee added successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("This Employee ID already exists.")

    with tab_edit:
        ids = employee_ids()
        if not ids:
            st.info("No employees available.")
        else:
            selected_label = st.selectbox("Select Employee", list(ids.keys()))
            selected_id = ids[selected_label]
            emp = get_employee(selected_id)

            if emp is not None:
                with st.form("edit_employee_form"):
                    c1, c2 = st.columns(2)
                    edit_name = c1.text_input("Name", value=str(emp["name"]))
                    edit_department = c2.selectbox(
                        "Department", DEPARTMENTS,
                        index=DEPARTMENTS.index(emp["department"])
                        if emp["department"] in DEPARTMENTS else 0
                    )
                    edit_designation = c1.text_input(
                        "Designation", value=str(emp["designation"] or "")
                    )
                    active = c2.checkbox(
                        "Active Employee", value=bool(emp["active"])
                    )

                    c1, c2, c3 = st.columns(3)
                    edit_basic = c1.number_input(
                        "Basic Salary", min_value=0.0,
                        value=float(emp["basic"] or 0)
                    )
                    edit_hra = c2.number_input(
                        "HRA", min_value=0.0,
                        value=float(emp["hra"] or 0)
                    )
                    edit_allowance = c3.number_input(
                        "Allowance", min_value=0.0,
                        value=float(emp["allowance"] or 0)
                    )

                    st.markdown("#### Education")
                    c1, c2 = st.columns(2)
                    edit_qualification = c1.text_input(
                        "Highest Qualification",
                        value=str(emp["highest_qualification"] or "")
                    )
                    edit_specialization = c2.text_input(
                        "Specialization",
                        value=str(emp["specialization"] or "")
                    )
                    edit_university = c1.text_input(
                        "University",
                        value=str(emp["university"] or "")
                    )
                    edit_year = c2.number_input(
                        "Graduation Year", min_value=0, max_value=2100,
                        value=int(emp["graduation_year"] or 0)
                    )

                    st.markdown("#### Experience")
                    c1, c2 = st.columns(2)
                    edit_experience = c1.number_input(
                        "Experience (Years)", min_value=0.0, step=0.5,
                        value=float(emp["experience_years"] or 0)
                    )
                    edit_previous = c2.text_input(
                        "Previous Company",
                        value=str(emp["previous_company"] or "")
                    )
                    old_joining = str(emp["joining_date"] or date.today())
                    try:
                        old_joining_date = date.fromisoformat(old_joining[:10])
                    except ValueError:
                        old_joining_date = date.today()
                    edit_joining = st.date_input(
                        "Joining Date", value=old_joining_date
                    )

                    save = st.form_submit_button(
                        "Save Changes", use_container_width=True
                    )

                    if save:
                        execute_sql("""
                            UPDATE employees SET
                                name=?, department=?, designation=?,
                                basic=?, hra=?, allowance=?, active=?,
                                highest_qualification=?, specialization=?,
                                university=?, graduation_year=?,
                                experience_years=?, previous_company=?,
                                joining_date=?
                            WHERE employee_id=?
                        """, (
                            edit_name.strip(), edit_department,
                            edit_designation.strip(), edit_basic, edit_hra,
                            edit_allowance, int(active), edit_qualification,
                            edit_specialization, edit_university,
                            edit_year if edit_year else None,
                            edit_experience, edit_previous,
                            edit_joining.isoformat(), selected_id
                        ))
                        st.success("Employee updated.")
                        st.rerun()

                if st.button("Delete Employee", type="secondary"):
                    with connect() as con:
                        con.execute(
                            "DELETE FROM attendance WHERE employee_id=?",
                            (selected_id,)
                        )
                        con.execute(
                            "DELETE FROM leaves WHERE employee_id=?",
                            (selected_id,)
                        )
                        con.execute(
                            "DELETE FROM payroll WHERE employee_id=?",
                            (selected_id,)
                        )
                        con.execute(
                            "DELETE FROM employees WHERE employee_id=?",
                            (selected_id,)
                        )
                    st.success("Employee and related records deleted.")
                    st.rerun()

    with tab_view:
        directory = read_sql("SELECT * FROM employees ORDER BY employee_id")
        if not directory.empty:
            search = st.text_input("Search name, ID, qualification or department")
            if search:
                mask = directory.astype(str).apply(
                    lambda col: col.str.contains(
                        search, case=False, na=False
                    )
                ).any(axis=1)
                directory = directory[mask]

            st.dataframe(directory, use_container_width=True, hide_index=True)

            st.subheader("Qualification Analysis")
            if not directory.empty:
                q = directory["highest_qualification"].replace(
                    "", "Not specified"
                ).value_counts().reset_index()
                q.columns = ["Qualification", "Employees"]
                st.plotly_chart(
                    px.bar(q, x="Qualification", y="Employees",
                           title="Employees by Qualification"),
                    use_container_width=True
                )

                st.subheader("Experience Analysis")
                st.plotly_chart(
                    px.histogram(
                        directory, x="experience_years", nbins=10,
                        title="Experience Distribution (Years)"
                    ),
                    use_container_width=True
                )

# =========================================================
# ATTENDANCE
# =========================================================
elif page == "Attendance":
    st.title("🗓️ Attendance Management")

    tab_post, tab_records = st.tabs(["Record Attendance", "View / Correct Records"])

    with tab_post:
        ids = employee_ids(active_only=True)
        if not ids:
            st.info("Add an active employee first.")
        else:
            with st.form("attendance_form"):
                chosen_label = st.selectbox("Employee", list(ids.keys()))
                emp_id = ids[chosen_label]
                work_date = st.date_input("Work Date", value=date.today())
                status = st.selectbox("Attendance Status", STATUSES)
                overtime = st.number_input(
                    "Overtime Hours", min_value=0.0, step=0.5
                )
                post = st.form_submit_button(
                    "Save Attendance", use_container_width=True
                )

                if post:
                    try:
                        execute_sql("""
                            INSERT INTO attendance
                                (employee_id, work_date, status, overtime)
                            VALUES (?, ?, ?, ?)
                        """, (
                            emp_id, work_date.isoformat(), status, overtime
                        ))
                        st.success("Attendance saved.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(
                            "Attendance already exists for this employee "
                            "and date. Use the correction section."
                        )

    with tab_records:
        records = read_sql("""
            SELECT a.id, a.employee_id, e.name, e.department,
                   a.work_date, a.status, a.overtime
            FROM attendance a
            JOIN employees e ON a.employee_id=e.employee_id
            ORDER BY a.work_date DESC
        """)

        if records.empty:
            st.info("No attendance records.")
        else:
            c1, c2 = st.columns(2)
            departments = ["All"] + sorted(
                records["department"].dropna().unique().tolist()
            )
            dept_filter = c1.selectbox("Department Filter", departments)
            status_filter = c2.selectbox(
                "Status Filter", ["All"] + STATUSES
            )

            filtered = records.copy()
            if dept_filter != "All":
                filtered = filtered[
                    filtered["department"] == dept_filter
                ]
            if status_filter != "All":
                filtered = filtered[filtered["status"] == status_filter]

            st.metric("Filtered Attendance Records", len(filtered))
            st.dataframe(filtered, use_container_width=True, hide_index=True)

            st.download_button(
                "Download Filtered Attendance CSV",
                filtered.to_csv(index=False).encode("utf-8"),
                "attendance.csv",
                "text/csv"
            )

            st.subheader("Status Count — All Records")
            status_counts = records.groupby("status").size().reset_index(
                name="Records"
            )
            st.dataframe(status_counts, use_container_width=True,
                         hide_index=True)
            st.write(f"Total records: **{len(records)}**")

            st.subheader("Correct or Delete Attendance")
            row_options = {
                f"ID {r.id}: {r.employee_id} | {r.work_date} | {r.status}":
                int(r.id)
                for r in records.itertuples()
            }
            selected_record = st.selectbox(
                "Select record", list(row_options.keys())
            )
            record_id = row_options[selected_record]
            selected_row = records[records["id"] == record_id].iloc[0]

            with st.form("correct_attendance"):
                new_status = st.selectbox(
                    "Correct Status", STATUSES,
                    index=STATUSES.index(selected_row["status"])
                )
                new_overtime = st.number_input(
                    "Correct Overtime Hours", min_value=0.0,
                    value=float(selected_row["overtime"] or 0), step=0.5
                )
                correct = st.form_submit_button("Update Record")

                if correct:
                    execute_sql("""
                        UPDATE attendance
                        SET status=?, overtime=?
                        WHERE id=?
                    """, (new_status, new_overtime, record_id))
                    st.success("Attendance updated.")
                    st.rerun()

            if st.button("Delete Selected Attendance"):
                execute_sql(
                    "DELETE FROM attendance WHERE id=?", (record_id,)
                )
                st.success("Attendance record deleted.")
                st.rerun()

# =========================================================
# EMPLOYEE-WISE ATTENDANCE COMPARISON
# =========================================================
elif page == "Attendance Comparison":
    st.title("📈 Employee Attendance Comparison")

    all_ids = employee_ids()
    if len(all_ids) < 2:
        st.info("Add at least two employees to compare.")
    else:
        chosen_labels = st.multiselect(
            "Choose two or more employees",
            list(all_ids.keys()),
            default=list(all_ids.keys())[:2]
        )
        month = st.text_input("Month (YYYY-MM)", value=date.today().strftime("%Y-%m"))

        try:
            datetime.strptime(month, "%Y-%m")
            valid_month = True
        except ValueError:
            valid_month = False
            st.error("Enter month in YYYY-MM format.")

        if valid_month and len(chosen_labels) >= 2:
            comparison = []

            for label in chosen_labels:
                emp_id = all_ids[label]
                df = get_month_attendance(emp_id, month)
                summary = attendance_summary(df)
                emp = get_employee(emp_id)

                comparison.append({
                    "Employee": emp["name"],
                    "Employee ID": emp_id,
                    "Department": emp["department"],
                    "Present": summary["Present"],
                    "Work From Home": summary["Work From Home"],
                    "Half Day": summary["Half Day"],
                    "Absent": summary["Absent"],
                    "Leave": summary["Leave"],
                    "Present Equivalent": summary["Present Equivalent"],
                    "Attendance %": round(summary["Attendance %"], 2),
                    "Overtime Hours": summary["Overtime Hours"]
                })

            comp = pd.DataFrame(comparison)
            st.dataframe(comp, use_container_width=True, hide_index=True)

            st.plotly_chart(
                px.bar(comp, x="Employee", y="Attendance %",
                       color="Department", title=f"Attendance Percentage — {month}"),
                use_container_width=True
            )

            long = comp.melt(
                id_vars=["Employee"],
                value_vars=["Present", "Work From Home", "Half Day",
                            "Absent", "Leave"],
                var_name="Status", value_name="Days"
            )
            st.plotly_chart(
                px.bar(long, x="Employee", y="Days", color="Status",
                       barmode="group", title="Attendance Status Comparison"),
                use_container_width=True
            )

            st.plotly_chart(
                px.bar(comp, x="Employee", y="Overtime Hours",
                       title="Overtime Hours Comparison"),
                use_container_width=True
            )
        elif valid_month:
            st.info("Select at least two employees.")

# =========================================================
# LEAVE MANAGEMENT
# =========================================================
elif page == "Leave Management":
    st.title("🏖️ Leave Management")

    tab_apply, tab_review = st.tabs(["Record Leave", "Review Leaves"])

    with tab_apply:
        ids = employee_ids()
        with st.form("leave_form"):
            label = st.selectbox("Employee", list(ids.keys()))
            emp_id = ids[label]
            start = st.date_input("Start Date", value=date.today())
            end = st.date_input("End Date", value=date.today())
            leave_type = st.selectbox("Leave Type", LEAVE_TYPES)
            days = st.number_input("Leave Days", min_value=0.5, value=1.0, step=0.5)
            submit = st.form_submit_button("Submit Leave")

            if submit:
                if end < start:
                    st.error("End date cannot be before start date.")
                else:
                    execute_sql("""
                        INSERT INTO leaves
                        (employee_id, start_date, end_date, leave_type, days, approval)
                        VALUES (?, ?, ?, ?, ?, 'Pending')
                    """, (
                        emp_id, start.isoformat(), end.isoformat(),
                        leave_type, days
                    ))
                    st.success("Leave request saved.")
                    st.rerun()

    with tab_review:
        leaves = read_sql("""
            SELECT l.id, l.employee_id, e.name, e.department,
                   l.start_date, l.end_date, l.leave_type,
                   l.days, l.approval
            FROM leaves l JOIN employees e
            ON l.employee_id=e.employee_id
            ORDER BY l.id DESC
        """)

        if leaves.empty:
            st.info("No leave requests yet.")
        else:
            st.dataframe(leaves, use_container_width=True, hide_index=True)
            leave_map = {
                f"ID {r.id}: {r.name} | {r.start_date} | {r.approval}":
                int(r.id)
                for r in leaves.itertuples()
            }
            selected = st.selectbox("Select leave request", list(leave_map.keys()))
            leave_id = leave_map[selected]
            approval = st.selectbox(
                "Decision", ["Pending", "Approved", "Rejected"]
            )

            if st.button("Update Leave Decision"):
                execute_sql(
                    "UPDATE leaves SET approval=? WHERE id=?",
                    (approval, leave_id)
                )
                st.success("Leave decision updated.")
                st.rerun()

# =========================================================
# PAYROLL
# =========================================================
elif page == "Salary & Payroll":
    st.title("💰 Salary & Payroll Management")

    tab_calculate, tab_saved = st.tabs(
        ["Calculate / Save Payroll", "Saved Payroll & Payments"]
    )

    with tab_calculate:
        ids = employee_ids(active_only=True)
        if not ids:
            st.info("Add an active employee first.")
        else:
            with st.form("payroll_form"):
                label = st.selectbox("Employee", list(ids.keys()))
                emp_id = ids[label]
                month = st.text_input(
                    "Payroll Month (YYYY-MM)",
                    value=date.today().strftime("%Y-%m")
                )

                try:
                    datetime.strptime(month, "%Y-%m")
                    valid_month = True
                except ValueError:
                    valid_month = False

                if valid_month:
                    attendance = get_month_attendance(emp_id, month)
                    summary = attendance_summary(attendance)

                    st.markdown("#### Attendance-Based Paid Days Estimate")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Present", summary["Present"])
                    c2.metric("Half Days", summary["Half Day"])
                    c3.metric("Work From Home", summary["Work From Home"])

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Absent", summary["Absent"])
                    c2.metric("Leave", summary["Leave"])
                    c3.metric("Overtime Hours Recorded",
                              summary["Overtime Hours"])

                    st.caption(
                        "Policy used: Present = 1 paid day, WFH = 1 paid day, "
                        "Half Day = 0.5 paid day. Leave, holidays and weekly offs "
                        "are excluded. Change this policy in your application "
                        "if your organization handles these differently."
                    )

                    default_paid = min(
                        summary["Paid Days"],
                        calendar.monthrange(
                            int(month[:4]), int(month[5:7])
                        )[1]
                    )
                else:
                    st.error("Use YYYY-MM format, such as 2026-10.")
                    default_paid = 0

                st.markdown("#### Payroll Inputs")
                c1, c2 = st.columns(2)
                paid_days = c1.number_input(
                    "Paid Days", min_value=0.0,
                    value=float(default_paid), step=0.5
                )
                overtime_hours = c2.number_input(
                    "Overtime Hours", min_value=0.0,
                    value=float(summary["Overtime Hours"]) if valid_month else 0.0,
                    step=0.5
                )

                c1, c2 = st.columns(2)
                hourly_rate = c1.number_input(
                    "Overtime Hourly Rate (₹)", min_value=0.0, value=100.0
                )
                bonus = c2.number_input("Bonus (₹)", min_value=0.0)

                deductions = st.number_input("Deductions (₹)", min_value=0.0)

                calculate = st.form_submit_button(
                    "Calculate and Save Payroll",
                    use_container_width=True
                )

                if calculate:
                    if not valid_month:
                        st.error("Correct the month format first.")
                    else:
                        emp = get_employee(emp_id)
                        result = calculate_payroll(
                            emp, month, paid_days, overtime_hours,
                            hourly_rate, bonus, deductions
                        )

                        execute_sql("""
                            INSERT INTO payroll (
                                employee_id, month, paid_days, bonus,
                                deductions, overtime_pay, gross, net,
                                payment_status, payment_date,
                                overtime_hours, hourly_rate
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Not Paid', NULL, ?, ?)
                            ON CONFLICT(employee_id, month)
                            DO UPDATE SET
                                paid_days=excluded.paid_days,
                                bonus=excluded.bonus,
                                deductions=excluded.deductions,
                                overtime_pay=excluded.overtime_pay,
                                gross=excluded.gross,
                                net=excluded.net,
                                overtime_hours=excluded.overtime_hours,
                                hourly_rate=excluded.hourly_rate
                        """, (
                            emp_id, month, result["paid_days"],
                            result["bonus"], result["deductions"],
                            result["overtime_pay"], result["gross"],
                            result["net"], result["overtime_hours"],
                            result["hourly_rate"]
                        ))

                        st.success("Payroll calculated and saved.")

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Base Pay", money(result["base_pay"]))
                        c2.metric(
                            "Overtime Cost",
                            f"{result['overtime_hours']:g} × "
                            f"{money(result['hourly_rate'])} = "
                            f"{money(result['overtime_pay'])}"
                        )
                        c3.metric("Net Salary", money(result["net"]))

                        st.write(
                            f"**Formula:** {money(result['base_pay'])} "
                            f"+ {money(result['overtime_pay'])} overtime "
                            f"+ {money(result['bonus'])} bonus "
                            f"− {money(result['deductions'])} deductions "
                            f"= **{money(result['net'])}**"
                        )

    with tab_saved:
        saved = read_sql("""
            SELECT p.id, p.employee_id, e.name, e.department,
                   p.month, p.paid_days, p.overtime_hours,
                   p.hourly_rate, p.overtime_pay, p.bonus,
                   p.deductions, p.gross, p.net,
                   p.payment_status, p.payment_date
            FROM payroll p
            JOIN employees e ON p.employee_id=e.employee_id
            ORDER BY p.month DESC, p.employee_id
        """)

        if saved.empty:
            st.info("No saved payroll records yet.")
        else:
            c1, c2 = st.columns(2)
            month_filter = c1.selectbox(
                "Month Filter", ["All"] + sorted(
                    saved["month"].dropna().unique().tolist(),
                    reverse=True
                )
            )
            status_filter = c2.selectbox(
                "Payment Filter", ["All", "Paid", "Not Paid"]
            )

            filtered = saved.copy()
            if month_filter != "All":
                filtered = filtered[filtered["month"] == month_filter]
            if status_filter != "All":
                filtered = filtered[
                    filtered["payment_status"] == status_filter
                ]

            paid = saved[saved["payment_status"] == "Paid"]["net"].sum()
            pending = saved[saved["payment_status"] != "Paid"]["net"].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("Saved Payroll", len(saved))
            c2.metric("Amount Paid", money(paid))
            c3.metric("Amount Pending", money(pending))

            st.dataframe(filtered, use_container_width=True, hide_index=True)

            st.subheader("Update Payment Status")
            pay_map = {
                f"{r.employee_id} | {r.name} | {r.month} | {money(r.net)}":
                int(r.id)
                for r in saved.itertuples()
            }
            chosen = st.selectbox("Select Payroll Record", list(pay_map.keys()))
            payroll_id = pay_map[chosen]
            current = saved[saved["id"] == payroll_id].iloc[0]

            with st.form("payment_update"):
                new_status = st.selectbox(
                    "Payment Status",
                    ["Not Paid", "Paid"],
                    index=0 if current["payment_status"] != "Paid" else 1
                )
                payment_date = st.date_input(
                    "Payment Date",
                    value=date.today()
                )
                update_payment = st.form_submit_button("Update Payment")

                if update_payment:
                    pay_date = (
                        payment_date.isoformat()
                        if new_status == "Paid" else None
                    )
                    execute_sql("""
                        UPDATE payroll
                        SET payment_status=?, payment_date=?
                        WHERE id=?
                    """, (new_status, pay_date, payroll_id))
                    st.success("Payment status updated.")
                    st.rerun()

            st.download_button(
                "Download Payroll CSV",
                filtered.to_csv(index=False).encode("utf-8"),
                "payroll.csv",
                "text/csv"
            )

            st.subheader("Salary Breakdown")
            chart_data = filtered.copy()
            if not chart_data.empty:
                st.plotly_chart(
                    px.bar(
                        chart_data, x="name",
                        y=["gross", "net"],
                        barmode="group",
                        title="Gross vs Net Salary"
                    ),
                    use_container_width=True
                )

# =========================================================
# DEPARTMENT COMPARISON
# =========================================================
elif page == "Department Comparison":
    st.title("🏢 Department Comparison")

    employees = read_sql("""
        SELECT employee_id, name, department, basic, hra, allowance
        FROM employees WHERE active=1
    """)
    attendance = read_sql("""
        SELECT employee_id, work_date, status, overtime
        FROM attendance
    """)
    payroll = read_sql("""
        SELECT employee_id, month, net, overtime_pay, payment_status
        FROM payroll
    """)

    if employees.empty:
        st.info("No active employees.")
    else:
        employees["monthly_salary"] = (
            employees["basic"] + employees["hra"] + employees["allowance"]
        )
        salary_dept = employees.groupby("department", as_index=False).agg(
            Headcount=("employee_id", "count"),
            Monthly_Salary_Cost=("monthly_salary", "sum")
        )

        st.subheader("Headcount and Salary Cost")
        st.dataframe(salary_dept, use_container_width=True, hide_index=True)
        st.plotly_chart(
            px.bar(salary_dept, x="department", y="Headcount",
                   color="department", title="Employees per Department"),
            use_container_width=True
        )
        st.plotly_chart(
            px.bar(salary_dept, x="department", y="Monthly_Salary_Cost",
                   color="department", title="Monthly Salary Cost"),
            use_container_width=True
        )

        if not attendance.empty:
            att = attendance.merge(
                employees[["employee_id", "department"]],
                on="employee_id", how="left"
            )
            overtime_dept = att.groupby(
                "department", as_index=False
            )["overtime"].sum()
            st.subheader("Overtime Hours by Department")
            st.plotly_chart(
                px.bar(overtime_dept, x="department", y="overtime",
                       color="department"),
                use_container_width=True
            )

            st.subheader("Attendance Status by Department")
            status_dept = att.groupby(
                ["department", "status"]
            ).size().reset_index(name="Records")
            st.plotly_chart(
                px.bar(status_dept, x="department", y="Records",
                       color="status", barmode="group"),
                use_container_width=True
            )

        if not payroll.empty:
            pay = payroll.merge(
                employees[["employee_id", "department"]],
                on="employee_id", how="left"
            )
            pay_dept = pay.groupby("department", as_index=False).agg(
                Net_Payroll=("net", "sum"),
                Overtime_Cost=("overtime_pay", "sum")
            )
            st.subheader("Payroll Comparison")
            st.dataframe(pay_dept, use_container_width=True, hide_index=True)
            st.plotly_chart(
                px.bar(pay_dept, x="department",
                       y=["Net_Payroll", "Overtime_Cost"],
                       barmode="group"),
                use_container_width=True
            )

# =========================================================
# MONTHLY REPORTS
# =========================================================
elif page == "Monthly Reports":
    st.title("📅 Monthly Reports")

    month = st.text_input(
        "Report Month (YYYY-MM)",
        value=date.today().strftime("%Y-%m")
    )

    try:
        datetime.strptime(month, "%Y-%m")
        valid_month = True
    except ValueError:
        valid_month = False
        st.error("Enter month in YYYY-MM format.")

    if valid_month:
        attendance = read_sql("""
            SELECT a.employee_id, e.name, e.department,
                   a.work_date, a.status, a.overtime
            FROM attendance a JOIN employees e
            ON a.employee_id=e.employee_id
            WHERE substr(a.work_date, 1, 7)=?
            ORDER BY e.department, e.name, a.work_date
        """, (month,))

        payroll = read_sql("""
            SELECT p.employee_id, e.name, e.department,
                   p.month, p.paid_days, p.overtime_hours,
                   p.overtime_pay, p.bonus, p.deductions,
                   p.gross, p.net, p.payment_status, p.payment_date
            FROM payroll p JOIN employees e
            ON p.employee_id=e.employee_id
            WHERE p.month=?
        """, (month,))

        c1, c2, c3 = st.columns(3)
        c1.metric("Attendance Records", len(attendance))
        c2.metric("Payroll Records", len(payroll))
        c3.metric(
            "Net Payroll", money(payroll["net"].sum() if not payroll.empty else 0)
        )

        st.subheader("Attendance Report")
        if attendance.empty:
            st.info("No attendance data for this month.")
        else:
            st.dataframe(attendance, use_container_width=True, hide_index=True)

            st.subheader("Attendance Status Totals")
            status_totals = attendance.groupby("status").size().reset_index(
                name="Records"
            )
            st.dataframe(status_totals, use_container_width=True, hide_index=True)

        st.subheader("Payroll Report")
        if payroll.empty:
            st.info("No payroll saved for this month.")
        else:
            st.dataframe(payroll, use_container_width=True, hide_index=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            attendance.to_excel(
                writer, sheet_name="Attendance", index=False
            )
            payroll.to_excel(
                writer, sheet_name="Payroll", index=False
            )

        st.download_button(
            "Download Monthly Report (Excel)",
            data=output.getvalue(),
            file_name=f"monthly_report_{month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# =========================================================
# EXPORT DATA
# =========================================================
elif page == "Export Data":
    st.title("📤 Export Data")

    exports = {
        "Employees": """
            SELECT * FROM employees ORDER BY employee_id
        """,
        "Attendance": """
            SELECT a.*, e.name, e.department
            FROM attendance a
            JOIN employees e ON a.employee_id=e.employee_id
            ORDER BY a.work_date DESC
        """,
        "Leaves": """
            SELECT l.*, e.name, e.department
            FROM leaves l
            JOIN employees e ON l.employee_id=e.employee_id
            ORDER BY l.start_date DESC
        """,
        "Payroll": """
            SELECT p.*, e.name, e.department
            FROM payroll p
            JOIN employees e ON p.employee_id=e.employee_id
            ORDER BY p.month DESC
        """
    }

    st.write("Download individual datasets as CSV or a combined Excel workbook.")

    for title, query in exports.items():
        df = read_sql(query)
        st.subheader(title)
        st.caption(f"{len(df)} records")
        st.download_button(
            f"Download {title} CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"{title.lower()}_export.csv",
            mime="text/csv",
            key=f"export_{title}"
        )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for title, query in exports.items():
            read_sql(query).to_excel(
                writer, sheet_name=title[:31], index=False
            )

    st.download_button(
        "Download All Data (Excel)",
        data=output.getvalue(),
        file_name="employee_system_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.sidebar.divider()
st.sidebar.caption("Employee Attendance & Salary Analysis System")
st.sidebar.caption("Academic demonstration prototype")
