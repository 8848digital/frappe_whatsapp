"""Run on each event."""
import html
import re

import frappe

from frappe.core.doctype.server_script.server_script_utils import EVENT_MAP
from frappe.utils import strip_html_tags

# Shortest / longest usable international number (E.164 allows 15 digits).
MIN_NUMBER_DIGITS = 10
MAX_NUMBER_DIGITS = 15

# Meta truncates body parameters beyond this.
MAX_PARAM_LENGTH = 1024


def run_server_script_for_doc_event(doc, event):
    """Run on each event."""
    if event not in EVENT_MAP:
        return

    if frappe.flags.in_install:
        return

    if frappe.flags.in_migrate:
        return
    
    if frappe.flags.in_uninstall:
        return

    notification = get_notifications_map().get(
        doc.doctype, {}
    ).get(EVENT_MAP[event], None)

    if notification:
        # run all scripts for this doctype + event
        for notification_name in notification:
            _schedule_whatsapp_notification(notification_name, doc)


def _schedule_whatsapp_notification(notification_name, doc):
    """Schedule WhatsApp notification to run after commit.

    Frappe v16 disallows frappe.db.commit() in doc hooks, so we defer
    the API call to after the transaction commits. This ensures share
    keys (for document print attachments) are persisted before the
    WhatsApp message containing their URL is sent to Meta.

    On Frappe v14/v15, after_commit is not available, so we call directly.
    """
    if hasattr(frappe.db, "after_commit"):
        # Frappe v16+: run after the doc-event transaction commits so that
        # share keys / set-property-after-alert writes are visible to Meta,
        # and commit our own writes (WhatsApp Message + Notification Log)
        # since we are outside the request's auto-commit scope.
        frappe.db.after_commit.add(
            lambda: _send_whatsapp_notification(
                notification_name, doc.doctype, doc.name, commit=True
            )
        )
    else:
        # Frappe v14/v15
        _send_whatsapp_notification(notification_name, doc.doctype, doc.name)


def _send_whatsapp_notification(notification_name, doctype, docname, commit=False):
    """Send WhatsApp notification."""
    try:
        doc = frappe.get_doc(doctype, docname)
        frappe.get_doc(
            "WhatsApp Notification",
            notification_name
        ).send_template_message(doc)
        if commit:
            # nosemgrep: frappe-manual-commit -- runs in after_commit callback outside request scope; WhatsApp Message + Notification Log rows rely on this to persist
            frappe.db.commit()
    except Exception:
        if commit:
            frappe.db.rollback()
        frappe.log_error(
            title=f"WhatsApp Notification failed: {notification_name}"
        )


def send_role_notifications(notification, data, numbers, reference_doctype=None, reference_name=None):
    """Send an already-built payload to role-resolved recipients.

    Runs as a background job: a role can resolve to dozens of people, and Meta
    rate-limits per phone number id, so a long fan-out must not block the
    request that triggered it. Field-based notifications still send inline.

    Only `to` differs between recipients; the payload was built once by
    send_template_message.
    """
    notification_doc = frappe.get_doc("WhatsApp Notification", notification)

    # notify() only reads doctype and name off this, so the reference is
    # rebuilt rather than carrying a whole document through the queue.
    doc_data = None
    if reference_doctype and reference_name:
        doc_data = frappe._dict(doctype=reference_doctype, name=reference_name)

    sent = 0
    for number in numbers:
        data["to"] = number
        try:
            if notification_doc.notify(data, doc_data):
                sent += 1
        except Exception:
            # One bad recipient must not strand the rest of the batch.
            frappe.log_error(
                title=f"WhatsApp role notification failed: {notification}",
                message=f"Recipient: {number}\n\n{frappe.get_traceback()}",
            )

    if sent and doc_data:
        notification_doc.apply_property_after_alert(doc_data)


def get_notifications_map():
    """Get mapping."""
    if cached_value:=frappe.cache().get_value("whatsapp_notification_map"):
        return cached_value
    if frappe.flags.in_patch and not frappe.db.table_exists("WhatsApp Notification"):
        return {}

    notification_map = {}
    enabled_whatsapp_notifications = frappe.get_all(
        "WhatsApp Notification",
        fields=("name", "reference_doctype", "doctype_event", "notification_type"),
        filters={"disabled": 0},
    )
    for notification in enabled_whatsapp_notifications:
        if notification.notification_type == "DocType Event":
            notification_map.setdefault(
                notification.reference_doctype, {}
            ).setdefault(
                notification.doctype_event, []
            ).append(notification.name)

    frappe.cache().set_value("whatsapp_notification_map", notification_map)

    return notification_map


def trigger_whatsapp_notifications_all():
    """Run all."""
    trigger_whatsapp_notifications("All")


def trigger_whatsapp_notifications_hourly():
    """Run hourly."""
    trigger_whatsapp_notifications("Hourly")


def trigger_whatsapp_notifications_daily():
    """Run daily."""
    trigger_whatsapp_notifications("Daily")


def trigger_whatsapp_notifications_weekly():
    """Trigger notification."""
    trigger_whatsapp_notifications("Weekly")


def trigger_whatsapp_notifications_monthly():
    """Trigger notification."""
    trigger_whatsapp_notifications("Monthly")


def trigger_whatsapp_notifications_yearly():
    """Trigger notification."""
    trigger_whatsapp_notifications("Yearly")


def trigger_whatsapp_notifications_hourly_long():
    """Trigger notification."""
    trigger_whatsapp_notifications("Hourly Long")


def trigger_whatsapp_notifications_daily_long():
    """Trigger notification."""
    trigger_whatsapp_notifications("Daily Long")


def trigger_whatsapp_notifications_weekly_long():
    """Trigger notification."""
    trigger_whatsapp_notifications("Weekly Long")


def trigger_whatsapp_notifications_monthly_long():
    """Trigger notification."""
    trigger_whatsapp_notifications("Monthly Long")


def trigger_whatsapp_notifications(event):
    """Run cron."""
    wa_notify_list = frappe.get_list(
        "WhatsApp Notification",
        filters={
            "event_frequency": event,
            "disabled": 0,
        }
    )

    for wa in wa_notify_list:
        frappe.get_doc(
            "WhatsApp Notification",
            wa.name,
        ).send_scheduled_message()

def get_whatsapp_account(phone_id=None, account_type='incoming'):
    """map whatsapp account with message"""
    if phone_id:
        account_name = frappe.db.get_value('WhatsApp Account', {'phone_id': phone_id}, 'name')
        if account_name:
            return frappe.get_doc("WhatsApp Account", account_name)

    account_field_type = 'is_default_incoming' if account_type =='incoming' else 'is_default_outgoing' 
    default_account_name = frappe.db.get_value('WhatsApp Account', {account_field_type: 1}, 'name')
    if default_account_name:
        return frappe.get_doc("WhatsApp Account", default_account_name)

    return None

def format_number(number):
    """Format number."""
    if number.startswith("+"):
        number = number[1 : len(number)]

    return number


def normalize_number(number, default_country_code=None):
    """Reduce a number to the digits-only form Meta expects.

    Unlike format_number, which only strips a leading "+", this copes with the
    way numbers are typed into User/Employee records: spaces, dashes, brackets,
    a national trunk prefix, or no country code at all.

    Returns None when the number cannot be used, so callers can skip the
    recipient and log it instead of sending a request Meta will reject.
    """
    if not number:
        return None

    digits = re.sub(r"\D", "", str(number))

    # Neither the international prefix nor the national trunk prefix are part
    # of the number Meta wants.
    if digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits.lstrip("0")

    if len(digits) == MIN_NUMBER_DIGITS and default_country_code:
        country_code = re.sub(r"\D", "", str(default_country_code))
        digits = f"{country_code}{digits}"

    # A bare national number with no country code to prepend is not dialable,
    # so anything still at the national length is rejected rather than sent.
    if len(digits) <= MIN_NUMBER_DIGITS or len(digits) > MAX_NUMBER_DIGITS:
        return None

    return digits


def sanitize_param(value):
    """Flatten a value into something Meta accepts as a template parameter.

    Meta rejects parameters containing newlines, tabs or four or more
    consecutive spaces, and renders any markup literally. Text Editor fields
    come back from get_formatted() wrapped in HTML, so strip that first.
    """
    if value is None:
        return ""

    value = html.unescape(strip_html_tags(str(value)))
    value = re.sub(r"\s+", " ", value).strip()

    if len(value) > MAX_PARAM_LENGTH:
        value = value[: MAX_PARAM_LENGTH - 3] + "..."

    return value