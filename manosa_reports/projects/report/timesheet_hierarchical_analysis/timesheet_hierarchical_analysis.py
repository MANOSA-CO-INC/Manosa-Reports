import frappe
from frappe import _
from frappe.utils import getdate, format_date, flt, get_first_day_of_week
from datetime import timedelta

def execute(filters=None):
    if not filters:
        filters = {}
    
    # Set default coverage dates to current work week (Monday to Friday)
    if not filters.get("coverage_from") and not filters.get("coverage_to"):
        monday = get_first_day_of_week(getdate())
        friday = monday + timedelta(days=4)
        filters["coverage_from"] = monday
        filters["coverage_to"] = friday
    
    columns = get_columns(filters)
    data = get_data(filters)
    summary = get_summary(data, filters)
    
    return columns, data, None, {}, summary

def get_columns(filters):
    grouping_raw = filters.get("grouping_combination", "")
    if ":" in grouping_raw:
        grouping = grouping_raw.split(":")[1]
    else:
        grouping = grouping_raw
    
    if grouping == "project_employee_activity":
        # Per Project View
        columns = [
            {"label": _("Project"), "fieldname": "project_name", "fieldtype": "Data", "width": 220},
            {"label": _("Employee"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
            {"label": _("Activity Type"), "fieldname": "activity_type", "fieldtype": "Link", "options": "Activity Type", "width": 180},
            {"label": _("Total Hours"), "fieldname": "total_hours", "fieldtype": "Float", "width": 120},
            {"label": _("Costing Amount"), "fieldname": "total_costing_amount", "fieldtype": "Currency", "width": 150},
            {"label": _("Employee Total Hours"), "fieldname": "employee_total_hours", "fieldtype": "Data", "width": 150},
        ]
    elif grouping == "project_activity_task":
        # Per Project Task View
        columns = [
            {"label": _("Project"), "fieldname": "project_name", "fieldtype": "Data", "width": 220},
            {"label": _("Activity Type"), "fieldname": "activity_type", "fieldtype": "Link", "options": "Activity Type", "width": 180},
            {"label": _("Task"), "fieldname": "task_name", "fieldtype": "Link", "options": "Task", "width": 280},
            {"label": _("Task Status"), "fieldname": "task_status", "fieldtype": "Data", "width": 120},
            {"label": _("Total Hours"), "fieldname": "total_hours", "fieldtype": "Float", "width": 120},
            {"label": _("Costing Amount"), "fieldname": "total_costing_amount", "fieldtype": "Currency", "width": 150},
        ]
    else:
        # Per Employee View (default)
        columns = [
            {"label": _("Employee"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
            {"label": _("Project"), "fieldname": "project_name", "fieldtype": "Data", "width": 220},
            {"label": _("Activity Type"), "fieldname": "activity_type", "fieldtype": "Link", "options": "Activity Type", "width": 180},
            {"label": _("Total Hours"), "fieldname": "total_hours", "fieldtype": "Float", "width": 120},
            {"label": _("Costing Amount"), "fieldname": "total_costing_amount", "fieldtype": "Currency", "width": 150},
            {"label": _("Employee Total Hours"), "fieldname": "employee_total_hours", "fieldtype": "Data", "width": 150},
        ]
    
    return columns

def get_data(filters):
    grouping_raw = filters.get("grouping_combination", "")
    if ":" in grouping_raw:
        grouping = grouping_raw.split(":")[1]
    else:
        grouping = grouping_raw
    
    coverage_from = filters.get("coverage_from")
    coverage_to = filters.get("coverage_to")
    
    if coverage_from and coverage_to:
        if getdate(coverage_from) > getdate(coverage_to):
            frappe.throw(_("Coverage From Date must be before or equal to Coverage To Date"))
    
    if grouping == "project_employee_activity":
        group_by_fields = "tsd.project, ts.employee, tsd.activity_type"
        select_fields = """
            ts.employee,
            emp.employee_name,
            tsd.project,
            proj.project_name,
            tsd.activity_type,
            SUM(tsd.hours) as total_hours,
            SUM(tsd.costing_amount) as total_costing_amount,
            '' as task
        """
        order_by = "tsd.project, ts.employee, tsd.activity_type"
        
    elif grouping == "project_activity_task":
        group_by_fields = "tsd.project, tsd.activity_type, tsd.task"
        select_fields = """
            tsd.project,
            proj.project_name,
            tsd.activity_type,
            tsd.task,
            SUM(tsd.hours) as total_hours,
            SUM(tsd.costing_amount) as total_costing_amount
        """
        order_by = "tsd.project, tsd.activity_type, tsd.task"
        
    else:
        group_by_fields = "ts.employee, tsd.project, tsd.activity_type"
        select_fields = """
            ts.employee,
            emp.employee_name,
            tsd.project,
            proj.project_name,
            tsd.activity_type,
            SUM(tsd.hours) as total_hours,
            SUM(tsd.costing_amount) as total_costing_amount,
            '' as task
        """
        order_by = "ts.employee, tsd.project, tsd.activity_type"
    
    conditions = "ts.docstatus = 1"
    
    if coverage_from:
        conditions = conditions + " AND ts.start_date >= '{}'".format(coverage_from)
    if coverage_to:
        conditions = conditions + " AND ts.start_date <= '{}'".format(coverage_to)
    
    if filters.get("employee"):
        conditions = conditions + " AND ts.employee = '{}'".format(filters.get("employee"))
    if filters.get("project"):
        conditions = conditions + " AND tsd.project = '{}'".format(filters.get("project"))
    if filters.get("activity_type"):
        conditions = conditions + " AND tsd.activity_type = '{}'".format(filters.get("activity_type"))
    if filters.get("task"):
        conditions = conditions + " AND tsd.task = '{}'".format(filters.get("task"))
    if filters.get("status"):
        conditions = conditions + " AND ts.status = '{}'".format(filters.get("status"))
    
    query = """
        SELECT 
            {}
        FROM `tabTimesheet` ts
        INNER JOIN `tabTimesheet Detail` tsd ON tsd.parent = ts.name
        LEFT JOIN `tabEmployee` emp ON emp.name = ts.employee
        LEFT JOIN `tabProject` proj ON proj.name = tsd.project
        WHERE {}
        GROUP BY {}
        ORDER BY {}
    """.format(select_fields, conditions, group_by_fields, order_by)
    
    data = frappe.db.sql(query, as_dict=True)
    
    if data:
        # Process task name and status for Per Project Task view
        if grouping == "project_activity_task":
            for row in data:
                task_code = row.get("task", "")
                if task_code:
                    # Fetch task details from Task doctype
                    task_details = frappe.db.get_value("Task", task_code, ["subject", "status"], as_dict=True)
                    if task_details:
                        # Use subject as task name (standard ERPNext field)
                        row["task_name"] = task_details.get("subject", task_code)
                        # Set task status
                        if task_details.get("status") == "Completed":
                            row["task_status"] = "Completed"
                        else:
                            row["task_status"] = "Open"
                    else:
                        row["task_name"] = task_code
                        row["task_status"] = ""
                else:
                    row["task_name"] = ""
                    row["task_status"] = ""
        
        # Add Employee Total Hours column for Per Employee and Per Project views
        if grouping == "employee_project_activity":
            data = add_employee_total_hours(data, group_by="employee_name")
        elif grouping == "project_employee_activity":
            data = add_employee_total_hours(data, group_by="employee_name")
        
        return list(data)
    else:
        return []

def add_employee_total_hours(data, group_by="employee_name"):
    """
    Calculate total hours per employee and show only in the last row of each employee's group.
    Shows 2 decimal places when there's a value, blank otherwise.
    """
    if not data:
        return data
    
    # Calculate total hours per employee
    employee_totals = {}
    for row in data:
        emp = row.get(group_by, "")
        if emp:
            if emp not in employee_totals:
                employee_totals[emp] = 0.0
            employee_totals[emp] += flt(row.get("total_hours", 0))
    
    # Find the last row index for each employee
    employee_last_index = {}
    for i, row in enumerate(data):
        emp = row.get(group_by, "")
        if emp:
            employee_last_index[emp] = i
    
    # Add employee_total_hours column - only in last row of each employee
    for i, row in enumerate(data):
        emp = row.get(group_by, "")
        if emp and i == employee_last_index.get(emp, -1):
            # This is the last row for this employee - show total with 2 decimal places
            row["employee_total_hours"] = "{:.2f}".format(employee_totals[emp])
        else:
            # Not the last row - show empty string (blank, not zero)
            row["employee_total_hours"] = ""
    
    return data

def get_summary(data, filters):
    if data is None or len(data) == 0:
        return [
            {"value": 0, "label": _("Total Hours"), "datatype": "Float"},
            {"value": 0, "label": _("Total Costing Amount"), "datatype": "Currency"},
            {"value": 0, "label": _("Grouped Entries"), "datatype": "Int"},
        ]
    
    total_hours = 0.0
    total_costing = 0.0
    
    for row in data:
        total_hours = total_hours + flt(row.get("total_hours"))
        total_costing = total_costing + flt(row.get("total_costing_amount"))
    
    total_entries = len(data)
    
    coverage_from = filters.get("coverage_from")
    coverage_to = filters.get("coverage_to")
    
    if coverage_from and coverage_to:
        coverage_label = "{} - {}".format(
            format_date(getdate(coverage_from)), 
            format_date(getdate(coverage_to))
        )
    elif coverage_from:
        coverage_label = "{} - Present".format(format_date(getdate(coverage_from)))
    elif coverage_to:
        coverage_label = "Start - {}".format(format_date(getdate(coverage_to)))
    else:
        coverage_label = "All Time"
    
    return [
        {"value": total_hours, "label": _("Total Hours"), "datatype": "Float"},
        {"value": total_costing, "label": _("Total Costing Amount"), "datatype": "Currency"},
        {"value": total_entries, "label": _("Grouped Entries"), "datatype": "Int"},
        {"value": coverage_label, "label": _("Coverage Period"), "datatype": "Data"},
    ]
