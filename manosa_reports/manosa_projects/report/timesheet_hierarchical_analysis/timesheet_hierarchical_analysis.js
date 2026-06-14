frappe.query_reports["Timesheet Hierarchical Analysis"] = {
    // NO "filters" key - let JSON handle it!
    
    "onload": function(report) {
        // Wait for filters to render
        setTimeout(() => {
            // 1. Customize Grouping Combination field
            const grouping_field = report.page.fields_dict.grouping_combination;
            if (grouping_field) {
                // Create user-friendly options
                const grouping_options = [
                    { value: "Per Employee:employee_project_activity", label: "Per Employee" },
                    { value: "Per Project:project_employee_activity", label: "Per Project" },
                    { value: "Per Project Task:project_activity_task", label: "Per Project Task" }
                ];
                
                // Convert to Autocomplete for better display
                grouping_field.df.fieldtype = "Autocomplete";
                grouping_field.set_data(grouping_options);
            }
            
            // 2. Customize Employee field (optional - shows name + code)
            const employee_field = report.page.fields_dict.employee;
            if (employee_field) {
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee",
                        fields: ["name", "employee_name"],
                        filters: { status: "Active" },
                        limit_page_length: 1000
                    },
                    callback: function(r) {
                        if (r.message) {
                            const options = r.message.map(emp => ({
                                value: emp.name,
                                label: `${emp.employee_name} (${emp.name})`
                            }));
                            
                            employee_field.df.fieldtype = "Autocomplete";
                            employee_field.set_data(options);
                        }
                    }
                });
            }
        }, 500);
    }
};
