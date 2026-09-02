"""Resolve WhatsApp notification recipients from roles.

Kept out of the notification controller because three send paths need it:
DocType events, date-based events (Days Before/After) and Scheduler events.
"""

import frappe

from frappe.utils.safe_exec import get_safe_globals

from frappe_whatsapp.utils import normalize_number

# Never notify the built-in accounts, matching what core Frappe's
# get_info_based_on_role does for the Email channel.
EXCLUDED_USERS = ("Administrator", "Guest")

SOURCE_USER_THEN_EMPLOYEE = "User Mobile No, then Employee"
SOURCE_EMPLOYEE_THEN_USER = "Employee, then User Mobile No"
SOURCE_USER_ONLY = "User Mobile No"
SOURCE_EMPLOYEE_ONLY = "Employee Cell Number"


def get_users_for_roles(roles):
    """Enabled users holding any of these roles, as a sorted list of names.

    One query for every role rather than one per role.
    """
    if not roles:
        return []

    users = frappe.get_all(
        "Has Role",
        # "Has Role" is also a child of Role Profile, so without this filter
        # the query returns rows that are not users at all.
        filters={"role": ("in", list(roles)), "parenttype": "User"},
        pluck="parent",
        ignore_permissions=True,
    )

    candidates = set(users) - set(EXCLUDED_USERS)
    if not candidates:
        return []

    enabled = frappe.get_all(
        "User",
        filters={"name": ("in", list(candidates)), "enabled": 1},
        pluck="name",
        ignore_permissions=True,
    )

    return sorted(enabled)


def _get_employee_number(user):
    """Cell number from the Employee linked to this user, if HRMS is installed."""
    if not frappe.db.exists("DocType", "Employee"):
        return None

    return frappe.db.get_value("Employee", {"user_id": user}, "cell_number")


def resolve_phone(user, source, user_numbers=None):
    """Raw phone number for a user, following the configured source order."""
    user_number = (user_numbers or {}).get(user)

    if source == SOURCE_USER_ONLY:
        return user_number
    if source == SOURCE_EMPLOYEE_ONLY:
        return _get_employee_number(user)
    if source == SOURCE_EMPLOYEE_THEN_USER:
        return _get_employee_number(user) or user_number

    # Default: User first, so the Employee lookup is skipped in the common case.
    return user_number or _get_employee_number(user)


def _matching_roles(notification, doc=None):
    """Roles whose row condition passes for this document."""
    roles = []
    for row in notification.recipients:
        if not row.receiver_by_role:
            continue

        if row.condition:
            if doc is None:
                # Scheduler events have no document to evaluate against.
                continue
            try:
                if not frappe.safe_eval(
                    row.condition, get_safe_globals(), {"doc": doc.as_dict()}
                ):
                    continue
            except Exception:
                frappe.log_error(
                    title="WhatsApp Notification: recipient condition failed",
                    message=(
                        f"Notification: {notification.name}\n"
                        f"Role: {row.receiver_by_role}\n"
                        f"Condition: {row.condition}\n\n"
                        f"{frappe.get_traceback()}"
                    ),
                )
                continue

        roles.append(row.receiver_by_role)

    return roles


def get_role_recipients(notification, doc=None):
    """Resolve the notification's role rows into (recipients, skipped).

    recipients: [{"user", "full_name", "phone"}] deduped by normalized number,
    so someone holding two matching roles is messaged once.
    skipped:    [{"user", "reason"}] for users with no usable number.
    """
    if not notification.get("recipients"):
        return [], []

    roles = _matching_roles(notification, doc)
    users = get_users_for_roles(roles)
    if not users:
        return [], []

    settings = frappe.get_cached_doc("WhatsApp Settings")
    source = settings.get("role_phone_source") or SOURCE_USER_THEN_EMPLOYEE
    country_code = settings.get("default_country_code")

    user_details = {
        u.name: u
        for u in frappe.get_all(
            "User",
            filters={"name": ("in", users)},
            fields=["name", "full_name", "mobile_no"],
            ignore_permissions=True,
        )
    }
    user_numbers = {name: d.mobile_no for name, d in user_details.items()}

    recipients = []
    skipped = []
    seen = set()

    for user in users:
        raw = resolve_phone(user, source, user_numbers)
        if not raw:
            skipped.append({"user": user, "reason": "no phone number"})
            continue

        phone = normalize_number(raw, country_code)
        if not phone:
            skipped.append({"user": user, "reason": f"unusable number: {raw}"})
            continue

        # Dedupe on the normalized number, so "+91..." and "91..." collapse.
        if phone in seen:
            continue
        seen.add(phone)

        details = user_details.get(user) or {}
        recipients.append(
            {"user": user, "full_name": details.get("full_name") or user, "phone": phone}
        )

    return recipients, skipped


def log_skipped(notification_name, skipped):
    """Record skipped recipients once per run, not once per user."""
    if not skipped:
        return

    lines = "\n".join(f"{s['user']}: {s['reason']}" for s in skipped)
    frappe.log_error(
        title="WhatsApp Notification: recipients skipped",
        message=(
            f"Notification: {notification_name}\n"
            f"{len(skipped)} recipient(s) had no usable WhatsApp number.\n\n{lines}"
        ),
    )
