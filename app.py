
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


setup_database()


# ---------- PAGE HEADER ----------
st.title("📊 Employee Attendance & Salary Analysis System")
st.caption(
    "Manage employees, attendance, leave, overtime, payroll, "
    "department comparisons and monthly reports."
)

st.warning(
    "Initial version: before entering real employee data online, "
    "configure administrator authentication and persistent database "
    "storage. Do not use a public, unprotected deployment for confidential data."
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
        "Total Net Payroll",
        f"₹{payroll['net'].sum():,.2f}" if not payroll.empty else "₹0.00"
    )

    if not employees.empty:
        left, right = st.columns(2)

        dept_count = (
            employees[employees["active"] == 1]
            .groupby("department", as_index=False)
            .size()
            .rename(columns={"size": "Employees"})
        )

        left.plotly_chart(
            px.bar(
                dept_count,
                x="department",
                y="Employees",
                title="Active Employees by Department"
            ),
            use_container_width=True
        )

        dept_salary = (
            employees[employees["active"] == 1]
            .groupby("department", as_index=False)["basic"]
            .sum()
        )

        right.plotly_chart(
            px.bar(
                dept_salary,
                x="department",
                y="basic",
                title="Monthly Basic Salary by Department"
            ),
            use_container_width=True
        )

    if not attendance.empty:
        st.subheader("Attendance Status")
        st.plotly_chart(
            px.pie(
                attendance,
                names="status",
                title="Attendance Record Distribution"
            ),
            use_container_width=True
        )

    if employees.empty:
        st.info("Start by adding employees in Employee Management.")


# ---------- EMPLOYEE MANAGEMENT ----------
elif page == "Employee Management":
    st.header("Employee Management")

    with st.expander("➕ Add New Employee", expanded=True):
        with st.form("add_employee", clear_on_submit=True):
            col1, col2 = st.columns(2)

            eid = col1.text_input("Employee ID").strip()
            name = col2.text_input("Full Name").strip()
            dept = col1.text_input("Department").strip()
            designation = col2.text_input("Designation").strip()

            basic = col1.number_input("Basic Monthly Salary (₹)", min_value=0.0)
            hra = col2.number_input("Monthly HRA (₹)", min_value=0.0)
            allowance = col1.number_input(
                "Other Monthly Allowances (₹)", min_value=0.0
            )

            submitted = st.form_submit_button("Add Employee")

            if submitted:
                if not eid or not name or not dept:
                    st.error("Employee ID, name and department are required.")
                else:
                    try:
                        run(
                            """INSERT INTO employees
                            (employee_id,name,department,designation,basic,hra,allowance)
                            VALUES(?,?,?,?,?,?,?)""",
                            (eid, name, dept, designation, basic, hra, allowance)
                        )
                        st.success("Employee added successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("This Employee ID already exists.")

    employees = read("SELECT * FROM employees ORDER BY employee_id")

    st.subheader("Edit or Delete Employee")

    if not employees.empty:
        eid = st.selectbox("Select Employee ID", employees["employee_id"])
        emp = employees[employees["employee_id"] == eid].iloc[0]

        with st.form("edit_employee"):
            name = st.text_input("Name", str(emp["name"]))
            dept = st.text_input("Department", str(emp["department"]))
            designation = st.text_input(
                "Designation", str(emp["designation"] or "")
            )
            basic = st.number_input(
                "Basic Salary (₹)", min_value=0.0, value=float(emp["basic"])
            )
            hra = st.number_input(
                "HRA (₹)", min_value=0.0, value=float(emp["hra"])
            )
            allowance = st.number_input(
                "Other Allowances (₹)",
                min_value=0.0,
                value=float(emp["allowance"])
            )
            active = st.checkbox("Active Employee", value=bool(emp["active"]))

            save = st.form_submit_button("Save Changes")

            if save:
                run(
                    """UPDATE employees SET name=?,department=?,designation=?,
                    basic=?,hra=?,allowance=?,active=? WHERE employee_id=?""",
                    (
                        name, dept, designation, basic, hra, allowance,
                        int(active), eid
                    )
                )
                st.success("Employee updated.")
                st.rerun()

        confirm = st.checkbox(
            "I confirm permanent deletion of this employee and their records."
        )

        if st.button("Delete Employee", disabled=not confirm):
            for table in ["attendance", "leaves", "payroll"]:
                run(f"DELETE FROM {table} WHERE employee_id=?", (eid,))
            run("DELETE FROM employees WHERE employee_id=?", (eid,))
            st.success("Employee and associated records deleted.")
            st.rerun()

    st.subheader("All Employee Records")
    st.dataframe(employees, use_container_width=True, hide_index=True)


# ---------- ATTENDANCE ----------
elif page == "Attendance":
    st.header("Attendance Management")

    if employees.empty:
        st.info("Add employees before recording attendance.")
    else:
        with st.form("attendance_form", clear_on_submit=True):
            eid = st.selectbox("Employee ID", employees["employee_id"])
            work_date = st.date_input("Attendance Date", value=date.today())

            status = st.selectbox(
                "Attendance Status",
                ["Present", "Absent", "Half Day", "Work From Home",
                 "Holiday", "Weekly Off"]
            )

            overtime = st.number_input(
                "Overtime Hours", min_value=0.0, step=0.5
            )

            save = st.form_submit_button("Save Attendance")

            if save:
                run(
                    """INSERT INTO attendance
                    (employee_id,work_date,status,overtime)
                    VALUES(?,?,?,?)
                    ON CONFLICT(employee_id,work_date)
                    DO UPDATE SET status=excluded.status,
                                  overtime=excluded.overtime""",
                    (eid, work_date.isoformat(), status, overtime)
                )
                st.success("Attendance saved or updated.")
                st.rerun()

    attendance = read("SELECT * FROM attendance ORDER BY work_date DESC")

    st.subheader("Attendance Records")
    st.dataframe(attendance, use_container_width=True, hide_index=True)

    if not attendance.empty:
        record_id = st.selectbox("Record ID to delete", attendance["id"])
        if st.button("Delete Attendance Record"):
            run("DELETE FROM attendance WHERE id=?", (int(record_id),))
            st.rerun()


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
                ["Casual Leave", "Sick Leave", "Earned Leave",
                 "Unpaid Leave", "Other"]
            )

            days = st.number_input("Number of Leave Days", min_value=0.5, step=0.5)
            approval = st.selectbox(
                "Approval Status", ["Pending", "Approved", "Rejected"]
            )

            save = st.form_submit_button("Save Leave")

            if save:
                if end < start:
                    st.error("End date cannot be earlier than start date.")
                else:
                    run(
                        """INSERT INTO leaves
                        (employee_id,start_date,end_date,leave_type,days,approval)
                        VALUES(?,?,?,?,?,?)""",
                        (
                            eid, start.isoformat(), end.isoformat(),
                            leave_type, days, approval
                        )
                    )
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
        "Calculation: prorated basic + HRA + allowances + overtime + bonus "
        "- deductions. Confirm your organization's payroll rules before use."
    )

    if employees.empty:
        st.info("Add employees first.")
    else:
        with st.form("payroll_form"):
            eid = st.selectbox("Employee ID", employees["employee_id"])
            month = st.text_input(
                "Payroll Month (YYYY-MM)", date.today().strftime("%Y-%m")
            )
            paid_days = st.number_input(
                "Paid Days", min_value=0.0, max_value=31.0, value=30.0, step=0.5
            )
            bonus = st.number_input("Bonus (₹)", min_value=0.0)
            deductions = st.number_input("Deductions (₹)", min_value=0.0)
            overtime_rate = st.number_input(
                "Overtime Rate per Hour (₹)", min_value=0.0
            )

            calculate = st.form_submit_button("Calculate and Save Payroll")

            if calculate:
                try:
                    year, mon = map(int, month.split("-"))
                    days_in_month = calendar.monthrange(year, mon)[1]

                    if len(month) != 7 or not 1 <= mon <= 12:
                        raise ValueError

                    emp = employees[employees["employee_id"] == eid].iloc[0]

                    att = read(
                        """SELECT SUM(overtime) AS hours FROM attendance
                        WHERE employee_id=? AND substr(work_date,1,7)=?""",
                        (eid, month)
                    )

                    hours = float(att["hours"].iloc[0] or 0)
                    monthly_salary = float(
                        emp["basic"] + emp["hra"] + emp["allowance"]
                    )

                    payable_days = min(paid_days, float(days_in_month))
                    base_pay = monthly_salary * payable_days / days_in_month
                    overtime_pay = hours * overtime_rate
                    gross = base_pay + overtime_pay + bonus
                    net = max(0.0, gross - deductions)

                    run(
                        """INSERT INTO payroll
                        (employee_id,month,paid_days,bonus,deductions,
                         overtime_pay,gross,net)
                        VALUES(?,?,?,?,?,?,?,?)
                        ON CONFLICT(employee_id,month)
                        DO UPDATE SET paid_days=excluded.paid_days,
                        bonus=excluded.bonus,deductions=excluded.deductions,
                        overtime_pay=excluded.overtime_pay,
                        gross=excluded.gross,net=excluded.net""",
                        (
                            eid, month, payable_days, bonus, deductions,
                            overtime_pay, gross, net
                        )
                    )

                    st.success("Payroll calculated and saved.")
                    a, b, c = st.columns(3)
                    a.metric("Gross Salary", f"₹{gross:,.2f}")
                    b.metric("Overtime Pay", f"₹{overtime_pay:,.2f}")
                    c.metric("Net Salary", f"₹{net:,.2f}")

                except (ValueError, TypeError):
                    st.error("Enter a valid month in YYYY-MM format, such as 2026-10.")

    payroll = read("SELECT * FROM payroll ORDER BY month DESC")
    st.subheader("Saved Payroll Records")
    st.dataframe(payroll, use_container_width=True, hide_index=True)


# ---------- DEPARTMENT COMPARISON ----------
elif page == "Department Comparison":
    st.header("Department Comparison")

    if employees.empty:
        st.info("Add employees to see department comparisons.")
    else:
        dept = (
            employees[employees["active"] == 1]
            .groupby("department", as_index=False)
            .agg(
                Employees=("employee_id", "count"),
                Basic_Salary=("basic", "sum"),
                HRA=("hra", "sum"),
                Allowances=("allowance", "sum")
            )
        )

        dept["Monthly_Total_Salary"] = (
            dept["Basic_Salary"] + dept["HRA"] + dept["Allowances"]
        )

        if not attendance.empty:
            att = attendance.merge(
                employees[["employee_id", "department"]],
                on="employee_id",
                how="left"
            )

            att_summary = att.groupby("department", as_index=False).agg(
                Attendance_Records=("id", "count"),
                Overtime_Hours=("overtime", "sum")
            )

            present_statuses = ["Present", "Work From Home"]
            present = (
                att[att["status"].isin(present_statuses)]
                .groupby("department")
                .size()
                .rename("Present_Records")
                .reset_index()
            )

            att_summary = att_summary.merge(
                present, on="department", how="left"
            )
            att_summary["Present_Records"] = (
                att_summary["Present_Records"].fillna(0)
            )
            att_summary["Attendance_Percent"] = (
                100 * att_summary["Present_Records"]
                / att_summary["Attendance_Records"]
            )

            dept = dept.merge(att_summary, on="department", how="left")

        left, right = st.columns(2)

        left.plotly_chart(
            px.bar(
                dept, x="department", y="Monthly_Total_Salary",
                title="Monthly Salary Cost by Department"
            ),
            use_container_width=True
        )

        right.plotly_chart(
            px.bar(
                dept, x="department", y="Employees",
                title="Employee Count by Department"
            ),
            use_container_width=True
        )

        if "Attendance_Percent" in dept.columns:
            st.plotly_chart(
                px.bar(
                    dept, x="department", y="Attendance_Percent",
                    title="Recorded Attendance Rate by Department",
                    range_y=[0, 100]
                ),
                use_container_width=True
            )

            st.plotly_chart(
                px.bar(
                    dept, x="department", y="Overtime_Hours",
                    title="Overtime Hours by Department"
                ),
                use_container_width=True
            )

        if not payroll.empty:
            p = payroll.merge(
                employees[["employee_id", "department"]],
                on="employee_id", how="left"
            )

            monthly = p.groupby(
                ["month", "department"], as_index=False
            )["net"].sum()

            st.plotly_chart(
                px.line(
                    monthly, x="month", y="net", color="department",
                    markers=True, title="Monthly Net Payroll by Department"
                ),
                use_container_width=True
            )

        st.dataframe(dept, use_container_width=True, hide_index=True)


# ---------- MONTHLY REPORTS ----------
elif page == "Monthly Reports":
    st.header("Monthly Reports")

    month = st.text_input(
        "Select Month (YYYY-MM)", date.today().strftime("%Y-%m")
    )

    try:
        year, mon = map(int, month.split("-"))
        if len(month) != 7 or not 1 <= mon <= 12:
            raise ValueError

        att_month = read(
            """SELECT * FROM attendance
            WHERE substr(work_date,1,7)=?""", (month,)
        )

        pay_month = read(
            "SELECT * FROM payroll WHERE month=?", (month,)
        )

        leave_month = read(
            """SELECT * FROM leaves
            WHERE substr(start_date,1,7)=? OR substr(end_date,1,7)=?""",
            (month, month)
        )

        st.subheader(f"Report for {calendar.month_name[mon]} {year}")

        a, b, c = st.columns(3)
        a.metric("Attendance Entries", len(att_month))
        b.metric("Leave Records", len(leave_month))
        c.metric(
            "Net Payroll",
            f"₹{pay_month['net'].sum():,.2f}" if not pay_month.empty else "₹0.00"
        )

        st.subheader("Attendance")
        st.dataframe(att_month, use_container_width=True, hide_index=True)

        st.subheader("Payroll")
        st.dataframe(pay_month, use_container_width=True, hide_index=True)

        st.subheader("Leave Records")
        st.dataframe(leave_month, use_container_width=True, hide_index=True)

        st.subheader("Attendance Status Summary")
        if not att_month.empty:
            summary = (
                att_month.groupby("status", as_index=False)
                .size()
                .rename(columns={"size": "Count"})
            )
            st.plotly_chart(
                px.bar(summary, x="status", y="Count",
                       title="Monthly Attendance Summary"),
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

    except (ValueError, TypeError):
        st.error("Enter a valid month, for example 2026-10.")


# ---------- EXPORT ----------
elif page == "Export Data":
    st.header("Export Data")

    datasets = {
        "Employees": employees,
        "Attendance": attendance,
        "Leaves": leaves,
        "Payroll": payroll
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

        st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "Download All Data (Excel Workbook)",
        data=export_excel(datasets),
        file_name="employee_attendance_salary_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.sidebar.divider()
st.sidebar.caption("Employee Attendance & Salary Analysis System")
st.sidebar.caption("Verify payroll policies before processing real salaries.")

