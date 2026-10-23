# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

from . import __version__ as app_version

app_name = "whatsapp_integration"
app_title = "WhatsApp Integration"
app_publisher = "8848 Digital LLP"
app_description = "Send and receive WhatsApp messages from Frappe through the Meta Cloud API"
app_email = "satya@8848digital.com"
app_license = "Proprietary"

custom_fixtures = [
    {
        "dt": "Custom Field",
        "filters": {"module": ["in", ["WhatsApp Integration"]]},
    }
]

commands = ["whatsapp_integration.commands.export_fixtures.export_fixtures"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/whatsapp_integration/css/whatsapp_integration.css"
app_include_js = "/assets/whatsapp_integration/js/whatsapp_integration.js"
# app_include_js = ["whatsapp_integration.js"]

# include js, css files in header of web template
# web_include_css = "/assets/whatsapp_integration/css/whatsapp_integration.css"
# web_include_js = "/assets/whatsapp_integration/js/whatsapp_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "whatsapp_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#   "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#   "methods": "whatsapp_integration.utils.jinja_methods",
#   "filters": "whatsapp_integration.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "whatsapp_integration.install.before_install"
# after_install = "whatsapp_integration.install.after_install"
after_migrate = "whatsapp_integration.migrate.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "whatsapp_integration.uninstall.before_uninstall"
# after_uninstall = "whatsapp_integration.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "whatsapp_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#   "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#   "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#   "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#   "*": {
#       "on_update": "method",
#       "on_cancel": "method",
#       "on_trash": "method"
#   }
# }

# Scheduled Tasks
# ---------------

# Sites that ran this app under its old package name have these URLs in
# Meta (webhook, Flow endpoint) and in other clients. Keep them working.
_LEGACY_PACKAGE = "frappe_whatsapp"
override_whitelisted_methods = {
    method.replace("whatsapp_integration", _LEGACY_PACKAGE, 1): method
    for method in (
        "whatsapp_integration.utils.webhook.webhook",
        "whatsapp_integration.whatsapp_integration.api.flow_endpoint.handle_flow_request",
        "whatsapp_integration.utils.bulk_messaging.get_progress",
        "whatsapp_integration.utils.bulk_messaging.retry_failed",
        "whatsapp_integration.utils.bulk_messaging.import_recipients",
        "whatsapp_integration.utils.bulk_messaging.schedule_bulk_messages",
        "whatsapp_integration.whatsapp_integration.doctype.whatsapp_flow.whatsapp_flow.get_whatsapp_flows",
        "whatsapp_integration.whatsapp_integration.doctype.whatsapp_flow.whatsapp_flow.import_flow_from_whatsapp",
        "whatsapp_integration.whatsapp_integration.doctype.whatsapp_flow.whatsapp_flow.sync_all_flows",
        "whatsapp_integration.whatsapp_integration.doctype.whatsapp_message.whatsapp_message.send_template",
        "whatsapp_integration.whatsapp_integration.doctype.whatsapp_notification.whatsapp_notification.call_trigger_notifications",
        "whatsapp_integration.whatsapp_integration.doctype.whatsapp_templates.whatsapp_templates.fetch",
    )
}

# Show linked WhatsApp Messages in every document's timeline.
additional_timeline_content = {
    "*": ["whatsapp_integration.utils.timeline.get_whatsapp_timeline"]
}

scheduler_events = {
    "all": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_all",
        "whatsapp_integration.utils.bulk_messaging.process_scheduled_bulk_messages"
    ],
    "hourly": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_hourly"
    ],
    "hourly_long": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_hourly_long"
    ],
    "daily": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_daily",
        "whatsapp_integration.whatsapp_integration.doctype.whatsapp_notification.whatsapp_notification.trigger_notifications",
    ],
    "daily_long": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_daily_long",
    ],
    "weekly": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_weekly",
    ],
    "weekly_long": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_weekly_long",
    ],
    "monthly": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_monthly",
    ],
    "monthly_long": [
        "whatsapp_integration.utils.trigger_whatsapp_notifications_monthly_long",
    ],
}

# Testing
# -------

# before_tests = "whatsapp_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#   "frappe.desk.doctype.event.event.get_events": "whatsapp_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#   "Task": "whatsapp_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
#   {
#       "doctype": "{doctype_1}",
#       "filter_by": "{filter_by}",
#       "redact_fields": ["{field_1}", "{field_2}"],
#       "partial": 1,
#   },
#   {
#       "doctype": "{doctype_2}",
#       "filter_by": "{filter_by}",
#       "partial": 1,
#   },
#   {
#       "doctype": "{doctype_3}",
#       "strict": False,
#   },
#   {
#       "doctype": "{doctype_4}"
#   }
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#   "whatsapp_integration.auth.validate"
# ]


doc_events = {
    "*": {
        "before_insert": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "after_insert": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "before_validate": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "validate": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "on_update": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "before_submit": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "on_submit": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "before_cancel": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "on_cancel": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "on_trash": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "after_delete": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "before_update_after_submit": "whatsapp_integration.utils.run_server_script_for_doc_event",
        "on_update_after_submit": "whatsapp_integration.utils.run_server_script_for_doc_event"
    }
}
