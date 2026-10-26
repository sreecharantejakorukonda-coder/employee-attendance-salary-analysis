

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import calendar
from datetime import date
from io import BytesIO

st.set_page_config(
    page_title="Employee Attendance & Salary Analysis",
    page_icon="📊",
    layout="wide"
)

DB = "employee_system.db"
STATUSES = [
    "Present", "Absent", "Half Day",
    "Work From Home", "Holiday", "Weekly Off"
]


# ---------- DATABASE ----------
def connect():
    return sqlite3.connect(DB)


def setup_database():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            designation TEXT,
            basic REAL DEFAULT 0,
            hra REAL DEFAULT 0,
            allowance REAL DEFAULT 0,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            work_date TEXT NOT NULL,
            status TEXT NOT NULL,
            overtime REAL DEFAULT 0,
            UNIQUE(employee_id, work_date)
        );

        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            days REAL NOT NULL,
            approval TEXT DEFAULT 'Pending'
        );

        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            month TEXT NOT NULL,
            paid_days REAL,
            bonus REAL DEFAULT 0,
            deductions REAL DEFAULT 0,
            overtime_pay REAL DEFAULT 0,
            gross REAL DEFAULT 0,
            net REAL DEFAULT 0,
            UNIQUE(employee_id, month)
        );
        """)


def read(sql, params=()):
    with connect() as con:
        return pd.read_sql_query(sql, con, params=params)


def run(sql, params=()):
    with connect() as con:
        con.execute(sql, params)


def export_excel(sheets):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return output.getvalue()


def valid_month(value):
    try:
        if len(value) != 7:
            return False
        year, month = map(int, value.split("-"))
        return year >= 1900 and 1 <= month <= 12
    except (ValueError, AttributeError):
        return False


# ---------- FICTIONAL DEMO DATA ----------
def add_demo_data():
    demo_employees = [
        ("EMP001", "Ravi Kumar", "IT", "Python Developer", 30000, 8000, 5000),
        ("EMP002", "Priya Sharma", "IT", "Data Analyst", 35000, 9000, 6000),
        ("EMP003", "Suresh Reddy", "HR", "HR Executive", 25000, 6000, 4000),
        ("EMP004", "Anjali Devi", "HR", "HR Manager", 40000, 10000, 7000),
        ("EMP005", "Kiran Kumar", "Finance", "Accountant", 28000, 7000, 3000),
        ("EMP006", "Sneha Rao", "Finance", "Finance Manager", 45000, 12000, 8000),
        ("EMP007", "Arjun Varma", "Marketing", "Marketing Executive", 26000, 6500, 4500),
        ("EMP008", "Divya Reddy", "Marketing", "Marketing Manager", 38000, 9500, 6000),
        ("EMP009", "Manoj Kumar", "IT", "ML Engineer", 42000, 11000, 7000),
        ("EMP010", "Pooja Singh", "HR", "Recruiter", 27000, 6500, 3500),
    ]

    attendance_rows = []

    # Sample attendance for September and October 2026.
    # Only weekdays are included. All records are fictional.
    for month, last_day in [("2026-09", 30), ("2026-10", 31)]:
        for day in range(1, last_day + 1):
            work_date = date.fromisoformat(f"{month}-{day:02d}")

            if work_date.weekday() >= 5:
                continue

            for i in range(1, 11):
                pattern = (day + i * 3) % 17

                if pattern == 0:
                    status = "Absent"
                elif pattern in (1, 2):
                    status = "Half Day"
                elif pattern == 3:
                    status = "Work From Home"
                else:
                    status = "Present"

                overtime = 2.0 if (day + i) % 9 == 0 else 0.0

                attendance_rows.append((
                    f"EMP{i:03d}",
                    work_date.isoformat(),
                    status,
                    overtime
                ))

    with connect() as con:
        con.executemany("""
            INSERT OR IGNORE INTO employees
            (employee_id, name, department, designation, basic, hra, allowance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, demo_employees)

        con.executemany("""
            INSERT OR IGNORE INTO attendance
            (employee_id, work_date, status, overtime)
            VALUES (?, ?, ?, ?)
        """, attendance_rows)

    return len(demo_employees), len(attendance_rows)


setup_database()


# ---------- HEADER AND NAVIGATION ----------
st.title("📊 Employee Attendance & Salary Analysis System")
st.caption(
    "Employee records • Bulk attendance • Leave • Payroll • "
    "Department analytics • Monthly reports"
)

st.warning(
    "Demo application: use fictional records only. Do not enter confidential "
    "employee or salary information in a public app without authentication "
    "and secure, persistent storage."
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Employee Management",
        "Attendance",
        "Leave Management",
        "Salary & Payroll",
        "Department Comparison",
        "Monthly Reports",
        "Export Data"
    ]
)

employees = read("SELECT * FROM employees ORDER BY employee_id")
attendance = read("SELECT * FROM attendance ORDER BY work_date DESC")
leaves = read("SELECT * FROM leaves ORDER BY start_date DESC")
payroll = read("SELECT * FROM payroll ORDER BY month DESC")


# ---------- DASHBOARD ----------
if page == "Dashboard":
    st.header("Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Employees", len(employees))
    c2.metric(
        "Active Employees",
        int(employees["active"].sum()) if not employees.empty else 0
    )
    c3.metric("Attendance Records", len(attendance))
    c4.metric(
        "Total Saved Net Payroll",
        f"₹{payroll['net'].sum():,.2f}"
        if not payroll.empty else "₹0.00"
    )

    if not employees.empty:
        active = employees[employees["active"] == 1].copy()
        active["monthly_total"] = (
            active["basic"] + active["hra"] + active["allowance"]
        )

        dept_count = (
            active.groupby("department", as_index=False)
            .size()
            .rename(columns={"size": "Employees"})
        )

        dept_salary = (
            active.groupby("department", as_index=False)["monthly_total"]
            .sum()
        )

        left, right = st.columns(2)

        left.plotly_chart(
            px.bar(
                dept_count,
                x="department",
                y="Employees",
                title="Active Employees by Department"
            ),
            use_container_width=True
        )

        right.plotly_chart(
            px.bar(
                dept_salary,
                x="department",
                y="monthly_total",
                title="Monthly Salary Cost by Department"
            ),
            use_container_width=True
        )

    if not attendance.empty:
        left, right = st.columns(2)

        status_summary = (
            attendance.groupby("status", as_index=False)
            .size()
            .rename(columns={"size": "Records"})
        )

        left.plotly_chart(
            px.pie(
                status_summary,
                names="status",
                values="Records",
                title="Attendance Status Distribution"
            ),
            use_container_width=True
        )

        monthly_att = attendance.copy()
        monthly_att["month"] = monthly_att["work_date"].str[:7]

        monthly_summary = (
            monthly_att.groupby(["month", "status"], as_index=False)
            .size()
            .rename(columns={"size": "Records"})
        )

        right.plotly_chart(
            px.bar(
                monthly_summary,
                x="month",
                y="Records",
                color="status",
                barmode="stack",
                title="Monthly Attendance Comparison"
            ),
            use_container_width=True
        )

    if employees.empty:
        st.info(
            "Open Employee Management or Attendance and load sample demo data."
        )


# ---------- EMPLOYEE MANAGEMENT ----------
elif page == "Employee Management":
    st.header("Employee Management")

    with st.expander("Load Sample Demo Data"):
        st.write(
            "Adds 10 fictional employees and September/October 2026 "
            "weekday attendance. Existing records are preserved."
        )

        if st.button("Load Demo Employees & Attendance", key="demo_employee"):
            emp_count, att_count = add_demo_data()
            st.success(
                f"Demo data checked: {emp_count} employees and "
                f"{att_count} attendance rows. Existing records were not overwritten."
            )
            st.rerun()

    with st.expander("Add New Employee", expanded=True):
        with st.form("add_employee", clear_on_submit=True):
            col1, col2 = st.columns(2)

            eid = col1.text_input("Employee ID").strip()
            name = col2.text_input("Full Name").strip()
            dept = col1.text_input("Department").strip()
            designation = col2.text_input("Designation").strip()

            basic = col1.number_input(
                "Basic Monthly Salary (₹)", min_value=0.0
            )
            hra = col2.number_input(
                "Monthly HRA (₹)", min_value=0.0
            )
            allowance = col1.number_input(
                "Other Monthly Allowances (₹)", min_value=0.0
            )

            submitted = st.form_submit_button("Add Employee")

            if submitted:
                if not eid or not name or not dept:
                    st.error(
                        "Employee ID, name and department are required."
                    )
                else:
                    try:
                        run("""
                            INSERT INTO employees
                            (employee_id, name, department, designation,
                             basic, hra, allowance)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            eid, name, dept, designation,
                            basic, hra, allowance
                        ))

                        st.success("Employee added successfully.")
                        st.rerun()

                    except sqlite3.IntegrityError:
                        st.error("This Employee ID already exists.")

    employees = read("SELECT * FROM employees ORDER BY employee_id")

    st.subheader("Edit or Delete Employee")

    if not employees.empty:
        eid = st.selectbox(
            "Select Employee ID",
            employees["employee_id"],
            key="employee_edit_id"
        )

        emp = employees[employees["employee_id"] == eid].iloc[0]

        with st.form("edit_employee"):
            name = st.text_input("Name", str(emp["name"]))
            dept = st.text_input("Department", str(emp["department"]))
            designation = st.text_input(
                "Designation", str(emp["designation"] or "")
            )

            basic = st.number_input(
                "Basic Salary (₹)",
                min_value=0.0,
                value=float(emp["basic"]),
                key="edit_basic"
            )

            hra = st.number_input(
                "HRA (₹)",
                min_value=0.0,
                value=float(emp["hra"]),
                key="edit_hra"
            )

            allowance = st.number_input(
                "Other Allowances (₹)",
                min_value=0.0,
                value=float(emp["allowance"]),
                key="edit_allowance"
            )

            active = st.checkbox(
                "Active Employee",
                value=bool(emp["active"])
            )

            save = st.form_submit_button("Save Changes")

            if save:
                run("""
                    UPDATE employees
                    SET name=?, department=?, designation=?,
                        basic=?, hra=?, allowance=?, active=?
                    WHERE employee_id=?
                """, (
                    name, dept, designation, basic,
                    hra, allowance, int(active), eid
                ))

                st.success("Employee updated.")
                st.rerun()

        confirm = st.checkbox(
            "I confirm permanent deletion of this employee and associated records.",
            key="confirm_employee_delete"
        )

        if st.button("Delete Employee", disabled=not confirm):
            with connect() as con:
                for table in ["attendance", "leaves", "payroll"]:
                    con.execute(
                        f"DELETE FROM {table} WHERE employee_id=?",
                        (eid,)
                    )

                con.execute(
                    "DELETE FROM employees WHERE employee_id=?",
                    (eid,)
                )

            st.success("Employee and associated records deleted.")
            st.rerun()

    st.subheader("All Employee Records")
    st.dataframe(
        employees,
        use_container_width=True,
        hide_index=True
    )


# ---------- ADVANCED ATTENDANCE ----------
elif page == "Attendance":
    st.header("Advanced Attendance Management")
    st.caption(
        "Bulk attendance, historical records, filters, corrections and analytics"
    )

    with st.expander("Load September & October 2026 Demo Data"):
        st.write(
            "Adds 10 fictional employees and synthetic weekday attendance. "
            "Existing records are preserved."
        )

        if st.button("Load Demo Employees & Attendance", key="demo_attendance"):
            emp_count, att_count = add_demo_data()
            st.success(
                f"Demo data checked: {emp_count} employees and "
                f"{att_count} attendance rows."
            )
            st.rerun()

    employees = read("""
        SELECT * FROM employees
        WHERE active=1
        ORDER BY employee_id
    """)

    if employees.empty:
        st.info("Add employees first or load demo data above.")

    else:
        st.subheader("1. Bulk Attendance Posting")

        work_date = st.date_input(
            "Select Attendance Date",
            value=date.today(),
            key="bulk_attendance_date"
        )

        existing = read("""
            SELECT employee_id, status, overtime
            FROM attendance
            WHERE work_date=?
        """, (work_date.isoformat(),))

        existing_map = (
            existing.set_index("employee_id").to_dict("index")
            if not existing.empty else {}
        )

        entry_df = employees[
            ["employee_id", "name", "department"]
        ].copy()

        entry_df["status"] = entry_df["employee_id"].map(
            lambda x: existing_map.get(x, {}).get("status", "Present")
        )

        entry_df["overtime"] = entry_df["employee_id"].map(
            lambda x: float(
                existing_map.get(x, {}).get("overtime", 0.0)
            )
        )

        st.info(
            "Choose each employee's status and overtime, then save "
            "attendance for everyone in one action."
        )

        edited_df = st.data_editor(
            entry_df,
            hide_index=True,
            use_container_width=True,
            disabled=["employee_id", "name", "department"],
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "Attendance Status",
                    options=STATUSES,
                    required=True
                ),
                "overtime": st.column_config.NumberColumn(
                    "Overtime Hours",
                    min_value=0.0,
                    max_value=24.0,
                    step=0.5,
                    format="%.1f"
                )
            },
            key=f"attendance_editor_{work_date.isoformat()}"
        )

        if st.button(
            "Save Attendance for All Employees",
            type="primary"
        ):
            if (
                edited_df["status"].isna().any()
                or (edited_df["overtime"] < 0).any()
                or (edited_df["overtime"] > 24).any()
            ):
                st.error("Check status and overtime values (0–24 hours).")

            else:
                with connect() as con:
                    con.executemany("""
                        INSERT INTO attendance
                        (employee_id, work_date, status, overtime)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(employee_id, work_date)
                        DO UPDATE SET
                            status=excluded.status,
                            overtime=excluded.overtime
                    """, [
                        (
                            row["employee_id"],
                            work_date.isoformat(),
                            row["status"],
                            float(row["overtime"])
                        )
                        for _, row in edited_df.iterrows()
                    ])

                st.success(
                    "Attendance saved or updated for all displayed employees."
                )
                st.rerun()

    attendance = read("""
        SELECT a.id, a.employee_id, e.name, e.department,
               a.work_date, a.status, a.overtime
        FROM attendance a
        LEFT JOIN employees e ON e.employee_id=a.employee_id
        ORDER BY a.work_date DESC, a.employee_id
    """)

    st.divider()
    st.subheader("2. Attendance Search & Filters")

    if not attendance.empty:
        f1, f2, f3 = st.columns(3)

        months = sorted(
            attendance["work_date"].str[:7].dropna().unique(),
            reverse=True
        )

        selected_month = f1.selectbox("Month", ["All"] + months)

        departments = sorted(
            attendance["department"].dropna().unique()
        )

        selected_dept = f2.selectbox(
            "Department", ["All"] + departments
        )

        statuses = sorted(
            attendance["status"].dropna().unique()
        )

        selected_status = f3.selectbox(
            "Status", ["All"] + statuses
        )

        search_id = st.text_input(
            "Search Employee ID or Name"
        ).strip().lower()

        filtered = attendance.copy()

        if selected_month != "All":
            filtered = filtered[
                filtered["work_date"].str.startswith(selected_month)
            ]

        if selected_dept != "All":
            filtered = filtered[
                filtered["department"] == selected_dept
            ]

        if selected_status != "All":
            filtered = filtered[
                filtered["status"] == selected_status
            ]

        if search_id:
            filtered = filtered[
                filtered["employee_id"].str.lower().str.contains(
                    search_id, na=False
                )
                | filtered["name"].str.lower().str.contains(
                    search_id, na=False
                )
            ]

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Filtered Attendance CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="attendance_report.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("3. Attendance Analytics")

        if not filtered.empty:
            m1, m2, m3, m4 = st.columns(4)

            m1.metric("Records", len(filtered))

            m2.metric(
                "Present / WFH",
                int(
                    filtered["status"].isin(
                        ["Present", "Work From Home"]
                    ).sum()
                )
            )

            m3.metric(
                "Absent",
                int((filtered["status"] == "Absent").sum())
            )

            m4.metric(
                "Overtime Hours",
                f"{filtered['overtime'].sum():.1f}"
            )

            left, right = st.columns(2)

            status_summary = (
                filtered.groupby("status", as_index=False)
                .size()
                .rename(columns={"size": "Records"})
            )

            left.plotly_chart(
                px.pie(
                    status_summary,
                    names="status",
                    values="Records",
                    title="Attendance Status Distribution"
                ),
                use_container_width=True
            )

            dept_summary = (
                filtered.groupby("department", as_index=False)
                .agg(
                    Attendance_Records=("id", "count"),
                    Overtime_Hours=("overtime", "sum")
                )
            )

            right.plotly_chart(
                px.bar(
                    dept_summary,
                    x="department",
                    y="Attendance_Records",
                    title="Attendance Records by Department"
                ),
                use_container_width=True
            )

            all_monthly = attendance.copy()
            all_monthly["month"] = all_monthly["work_date"].str[:7]

            monthly_summary = (
                all_monthly.groupby(["month", "status"], as_index=False)
                .size()
                .rename(columns={"size": "Records"})
            )

            st.plotly_chart(
                px.bar(
                    monthly_summary,
                    x="month",
                    y="Records",
                    color="status",
                    barmode="stack",
                    title="Month-to-Month Attendance Comparison"
                ),
                use_container_width=True
            )

            dept_overtime = (
                filtered.groupby("department", as_index=False)["overtime"]
                .sum()
            )

            st.plotly_chart(
                px.bar(
                    dept_overtime,
                    x="department",
                    y="overtime",
                    title="Overtime Hours by Department"
                ),
                use_container_width=True
            )

            rate_data = filtered.copy()
            rate_data["present_equivalent"] = (
                rate_data["status"]
                .map({
                    "Present": 1.0,
                    "Work From Home": 1.0,
                    "Half Day": 0.5
                })
                .fillna(0)
            )

            rates = (
                rate_data.groupby(
                    ["employee_id", "name", "department"],
                    as_index=False
                )
                .agg(
                    Recorded_Days=("id", "count"),
                    Present_Equivalent=("present_equivalent", "sum")
                )
            )

            rates["Recorded_Attendance_Percent"] = (
                100 * rates["Present_Equivalent"] / rates["Recorded_Days"]
            ).round(1)

            st.subheader("Recorded Attendance Rate by Employee")
            st.caption(
                "Based on entries in the selected filters; this is not "
                "a statutory payroll attendance measure."
            )

            st.plotly_chart(
                px.bar(
                    rates,
                    x="employee_id",
                    y="Recorded_Attendance_Percent",
                    color="department",
                    title="Recorded Attendance Rate by Employee",
                    range_y=[0, 100]
                ),
                use_container_width=True
            )

        else:
            st.info("No records match the selected filters.")

        st.divider()
        st.subheader("4. Correct or Delete Attendance")

        record_ids = attendance["id"].tolist()

        if record_ids:
            record_id = st.selectbox(
                "Select Attendance Record ID",
                record_ids
            )

            selected_record = attendance[
                attendance["id"] == record_id
            ].iloc[0]

            with st.form("edit_attendance_record"):
                new_status = st.selectbox(
                    "Correct Status",
                    STATUSES,
                    index=STATUSES.index(selected_record["status"])
                )

                new_overtime = st.number_input(
                    "Correct Overtime Hours",
                    min_value=0.0,
                    max_value=24.0,
                    value=float(selected_record["overtime"]),
                    step=0.5
                )

                update_record = st.form_submit_button(
                    "Update Attendance Record"
                )

                if update_record:
                    run("""
                        UPDATE attendance
                        SET status=?, overtime=?
                        WHERE id=?
                    """, (new_status, new_overtime, int(record_id)))

                    st.success("Attendance record updated.")
                    st.rerun()

            if st.button("Delete Selected Attendance Record"):
                run(
                    "DELETE FROM attendance WHERE id=?",
                    (int(record_id),)
                )
                st.success("Attendance record deleted.")
                st.rerun()

    else:
        st.info(
            "No attendance records yet. Post attendance or load demo data."
        )


# ---------- LEAVE MANAGEMENT ----------
elif page == "Leave Management":
    st.header("Leave Management")

    if employees.empty:
        st.info("Add employees first.")

    else:
        with st.form("leave_form", clear_on_submit=True):
            eid = st.selectbox("Employee ID", employees["employee_id"])
            start = st.date_input("Leave Start Date", value=date.today())
            end = st.date_input("Leave End Date", value=date.today())

            leave_type = st.selectbox(
                "Leave Type",
                [
                    "Casual Leave", "Sick Leave", "Earned Leave",
                    "Unpaid Leave", "Other"
                ]
            )

            days = st.number_input(
                "Number of Leave Days",
                min_value=0.5,
                step=0.5
            )

            approval = st.selectbox(
                "Approval Status",
                ["Pending", "Approved", "Rejected"]
            )

            save = st.form_submit_button("Save Leave")

            if save:
                if end < start:
                    st.error("End date cannot be earlier than start date.")
                else:
                    run("""
                        INSERT INTO leaves
                        (employee_id, start_date, end_date, leave_type, days, approval)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        eid, start.isoformat(), end.isoformat(),
                        leave_type, days, approval
                    ))

                    st.success("Leave record saved.")
                    st.rerun()

    leaves = read("SELECT * FROM leaves ORDER BY start_date DESC")
    st.dataframe(leaves, use_container_width=True, hide_index=True)

    if not leaves.empty:
        leave_id = st.selectbox("Leave record ID to delete", leaves["id"])

        if st.button("Delete Leave Record"):
            run("DELETE FROM leaves WHERE id=?", (int(leave_id),))
            st.rerun()


# ---------- SALARY & PAYROLL ----------
elif page == "Salary & Payroll":
    st.header("Salary Calculation & Payroll")

    st.write(
        "Demo calculation: prorated monthly salary + overtime + bonus − deductions."
    )

    st.caption(
        "This is an illustrative rule. Confirm the organization's payroll policy before real use."
    )

    if employees.empty:
        st.info("Add employees first.")

    else:
        with st.form("payroll_form"):
            eid = st.selectbox("Employee ID", employees["employee_id"])

            month = st.text_input(
                "Payroll Month (YYYY-MM)",
                date.today().strftime("%Y-%m")
            )

            use_attendance = st.checkbox(
                "Estimate paid days from attendance records for this month",
                value=False
            )

            manual_paid_days = st.number_input(
                "Paid Days (used when automatic estimate is off)",
                min_value=0.0,
                max_value=31.0,
                value=30.0,
                step=0.5
            )

            bonus = st.number_input("Bonus (₹)", min_value=0.0)
            deductions = st.number_input("Deductions (₹)", min_value=0.0)

            overtime_rate = st.number_input(
                "Overtime Rate per Hour (₹)",
                min_value=0.0,
                value=200.0
            )

            calculate = st.form_submit_button(
                "Calculate and Save Payroll"
            )

            if calculate:
                if not valid_month(month):
                    st.error(
                        "Enter a valid month in YYYY-MM format, for example 2026-10."
                    )

                else:
                    year, mon = map(int, month.split("-"))
                    days_in_month = calendar.monthrange(year, mon)[1]

                    emp = employees[
                        employees["employee_id"] == eid
                    ].iloc[0]

                    att = read("""
                        SELECT work_date, status, overtime
                        FROM attendance
                        WHERE employee_id=?
                        AND substr(work_date, 1, 7)=?
                    """, (eid, month))

                    hours = (
                        float(att["overtime"].sum())
                        if not att.empty else 0.0
                    )

                    if use_attendance:
                        # Illustrative estimate:
                        # Present/WFH = 1 day; Half Day = 0.5 day.
                        # Holidays, weekly offs, and leave approvals
                        # need the organization's actual payroll policy.
                        weights = {
                            "Present": 1.0,
                            "Work From Home": 1.0,
                            "Half Day": 0.5
                        }

                        paid_days = (
                            float(
                                att["status"].map(weights).fillna(0).sum()
                            )
                            if not att.empty else 0.0
                        )

                        paid_days = min(
                            paid_days,
                            float(days_in_month)
                        )

                    else:
                        paid_days = min(
                            manual_paid_days,
                            float(days_in_month)
                        )

                    monthly_salary = float(
                        emp["basic"] + emp["hra"] + emp["allowance"]
                    )

                    base_pay = (
                        monthly_salary * paid_days / days_in_month
                    )

                    overtime_pay = hours * overtime_rate
                    gross = base_pay + overtime_pay + bonus
                    net = max(0.0, gross - deductions)

                    run("""
                        INSERT INTO payroll
                        (employee_id, month, paid_days, bonus, deductions,
                         overtime_pay, gross, net)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(employee_id, month)
                        DO UPDATE SET
                            paid_days=excluded.paid_days,
                            bonus=excluded.bonus,
                            deductions=excluded.deductions,
                            overtime_pay=excluded.overtime_pay,
                            gross=excluded.gross,
                            net=excluded.net
                    """, (
                        eid, month, paid_days, bonus, deductions,
                        overtime_pay, gross, net
                    ))

                    st.success(f"Payroll saved for {eid} — {month}")

                    a, b, c, d = st.columns(4)
                    a.metric("Paid Days", f"{paid_days:g}")
                    b.metric("Base Pay", f"₹{base_pay:,.2f}")
                    c.metric("Overtime Pay", f"₹{overtime_pay:,.2f}")
                    d.metric("Net Salary", f"₹{net:,.2f}")

    payroll = read("""
        SELECT p.*, e.name, e.department
        FROM payroll p
        LEFT JOIN employees e ON e.employee_id=p.employee_id
        ORDER BY p.month DESC, p.employee_id
    """)

    st.subheader("Saved Payroll Records")
    st.dataframe(payroll, use_container_width=True, hide_index=True)


# ---------- DEPARTMENT COMPARISON ----------
elif page == "Department Comparison":
    st.header("Department Comparison")

    if employees.empty:
        st.info("Add employees or load demo data.")

    else:
        active = employees[employees["active"] == 1].copy()
        active["monthly_total"] = (
            active["basic"] + active["hra"] + active["allowance"]
        )

        dept = active.groupby("department", as_index=False).agg(
            Employees=("employee_id", "count"),
            Basic_Salary=("basic", "sum"),
            HRA=("hra", "sum"),
            Allowances=("allowance", "sum"),
            Monthly_Total_Salary=("monthly_total", "sum")
        )

        left, right = st.columns(2)

        left.plotly_chart(
            px.bar(
                dept,
                x="department",
                y="Monthly_Total_Salary",
                title="Monthly Salary Cost by Department"
            ),
            use_container_width=True
        )

        right.plotly_chart(
            px.bar(
                dept,
                x="department",
                y="Employees",
                title="Active Employees by Department"
            ),
            use_container_width=True
        )

        att = read("""
            SELECT a.*, e.department
            FROM attendance a
            LEFT JOIN employees e ON e.employee_id=a.employee_id
        """)

        if not att.empty:
            month_options = sorted(
                att["work_date"].str[:7].unique(),
                reverse=True
            )

            chosen_month = st.selectbox(
                "Attendance Month for Comparison",
                ["All"] + month_options
            )

            if chosen_month != "All":
                att = att[
                    att["work_date"].str.startswith(chosen_month)
                ]

            att["present_equivalent"] = (
                att["status"]
                .map({
                    "Present": 1.0,
                    "Work From Home": 1.0,
                    "Half Day": 0.5
                })
                .fillna(0)
            )

            att_summary = att.groupby(
                "department", as_index=False
            ).agg(
                Attendance_Records=("id", "count"),
                Present_Equivalent=("present_equivalent", "sum"),
                Overtime_Hours=("overtime", "sum")
            )

            att_summary["Recorded_Attendance_Percent"] = (
                100 * att_summary["Present_Equivalent"]
                / att_summary["Attendance_Records"]
            ).round(1)

            left, right = st.columns(2)

            left.plotly_chart(
                px.bar(
                    att_summary,
                    x="department",
                    y="Recorded_Attendance_Percent",
                    title="Recorded Attendance Rate by Department",
                    range_y=[0, 100]
                ),
                use_container_width=True
            )

            right.plotly_chart(
                px.bar(
                    att_summary,
                    x="department",
                    y="Overtime_Hours",
                    title="Overtime Hours by Department"
                ),
                use_container_width=True
            )

            st.dataframe(
                dept.merge(att_summary, on="department", how="left"),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.dataframe(dept, use_container_width=True, hide_index=True)

        payroll_data = read("""
            SELECT p.month, p.net, e.department
            FROM payroll p
            LEFT JOIN employees e ON e.employee_id=p.employee_id
        """)

        if not payroll_data.empty:
            monthly = payroll_data.groupby(
                ["month", "department"], as_index=False
            )["net"].sum()

            st.plotly_chart(
                px.line(
                    monthly,
                    x="month",
                    y="net",
                    color="department",
                    markers=True,
                    title="Monthly Net Payroll by Department"
                ),
                use_container_width=True
            )


# ---------- MONTHLY REPORTS ----------
elif page == "Monthly Reports":
    st.header("Monthly Reports")

    month = st.text_input(
        "Select Month (YYYY-MM)",
        date.today().strftime("%Y-%m")
    )

    if not valid_month(month):
        st.error("Enter a valid month, for example 2026-10.")

    else:
        att_month = read("""
            SELECT a.*, e.name, e.department
            FROM attendance a
            LEFT JOIN employees e ON e.employee_id=a.employee_id
            WHERE substr(a.work_date, 1, 7)=?
            ORDER BY a.work_date, a.employee_id
        """, (month,))

        pay_month = read("""
            SELECT p.*, e.name, e.department
            FROM payroll p
            LEFT JOIN employees e ON e.employee_id=p.employee_id
            WHERE p.month=?
        """, (month,))

        leave_month = read("""
            SELECT l.*, e.name, e.department
            FROM leaves l
            LEFT JOIN employees e ON e.employee_id=l.employee_id
            WHERE substr(l.start_date, 1, 7)=?
               OR substr(l.end_date, 1, 7)=?
        """, (month, month))

        year, mon = map(int, month.split("-"))

        st.subheader(
            f"Report for {calendar.month_name[mon]} {year}"
        )

        a, b, c = st.columns(3)
        a.metric("Attendance Entries", len(att_month))
        b.metric("Leave Records", len(leave_month))
        c.metric(
            "Net Payroll",
            f"₹{pay_month['net'].sum():,.2f}"
            if not pay_month.empty else "₹0.00"
        )

        st.subheader("Attendance")
        st.dataframe(
            att_month,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Payroll")
        st.dataframe(
            pay_month,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Leave Records")
        st.dataframe(
            leave_month,
            use_container_width=True,
            hide_index=True
        )

        if not att_month.empty:
            summary = (
                att_month.groupby("status", as_index=False)
                .size()
                .rename(columns={"size": "Count"})
            )

            st.plotly_chart(
                px.bar(
                    summary,
                    x="status",
                    y="Count",
                    title="Monthly Attendance Summary"
                ),
                use_container_width=True
            )

        st.download_button(
            "Download Monthly Report (Excel)",
            data=export_excel({
                "Attendance": att_month,
                "Payroll": pay_month,
                "Leaves": leave_month
            }),
            file_name=f"monthly_report_{month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ---------- EXPORT DATA ----------
elif page == "Export Data":
    st.header("Export Data")

    datasets = {
        "Employees": read("SELECT * FROM employees"),
        "Attendance": read("""
            SELECT a.*, e.name, e.department
            FROM attendance a
            LEFT JOIN employees e ON e.employee_id=a.employee_id
        """),
        "Leaves": read("""
            SELECT l.*, e.name, e.department
            FROM leaves l
            LEFT JOIN employees e ON e.employee_id=l.employee_id
        """),
        "Payroll": read("""
            SELECT p.*, e.name, e.department
            FROM payroll p
            LEFT JOIN employees e ON e.employee_id=p.employee_id
        """)
    }

    for name, df in datasets.items():
        st.subheader(name)

        st.download_button(
            f"Download {name} CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{name.lower()}.csv",
            mime="text/csv",
            key=f"csv_{name}"
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    st.download_button(
        "Download All Data (Excel Workbook)",
        data=export_excel(datasets),
        file_name="employee_attendance_salary_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


st.sidebar.divider()
st.sidebar.caption("Employee Attendance & Salary Analysis System")
st.sidebar.caption(
    "Use demo data for presentations; verify payroll rules before real use."
)
