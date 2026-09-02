# Copyright (c) 2026, Shridhar Patil and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe_whatsapp.testing import IntegrationTestCase

from frappe_whatsapp.utils.recipients import (
    SOURCE_EMPLOYEE_ONLY,
    SOURCE_EMPLOYEE_THEN_USER,
    SOURCE_USER_ONLY,
    SOURCE_USER_THEN_EMPLOYEE,
    get_role_recipients,
    get_users_for_roles,
    resolve_phone,
)

ROLE = "_Test WA Role"
OTHER_ROLE = "_Test WA Role Two"


def _make_user(email, mobile_no, roles, enabled=1):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": email.split("@")[0],
            "mobile_no": mobile_no,
            "enabled": enabled,
            "roles": [{"role": r} for r in roles],
        }
    )
    user.insert(ignore_permissions=True)
    return user


class TestGetUsersForRoles(IntegrationTestCase):
    """Tests for role -> user resolution."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for role in (ROLE, OTHER_ROLE):
            if not frappe.db.exists("Role", role):
                frappe.get_doc({"doctype": "Role", "role_name": role}).insert(
                    ignore_permissions=True
                )

        _make_user("wa_one@example.com", "9876543210", [ROLE])
        _make_user("wa_two@example.com", "+91 98765 43211", [ROLE, OTHER_ROLE])
        _make_user("wa_disabled@example.com", "9876543212", [ROLE], enabled=0)
        _make_user("wa_nophone@example.com", None, [ROLE])
        frappe.db.commit()  # nosemgrep: frappe-manual-commit -- test fixture setup

    def test_returns_users_with_role(self):
        users = get_users_for_roles([ROLE])
        self.assertIn("wa_one@example.com", users)
        self.assertIn("wa_two@example.com", users)

    def test_excludes_disabled_users(self):
        self.assertNotIn("wa_disabled@example.com", get_users_for_roles([ROLE]))

    def test_excludes_builtin_accounts(self):
        users = get_users_for_roles([ROLE, "System Manager"])
        self.assertNotIn("Administrator", users)
        self.assertNotIn("Guest", users)

    def test_user_with_two_matching_roles_listed_once(self):
        users = get_users_for_roles([ROLE, OTHER_ROLE])
        self.assertEqual(users.count("wa_two@example.com"), 1)

    def test_empty_roles_returns_empty(self):
        self.assertEqual(get_users_for_roles([]), [])
        self.assertEqual(get_users_for_roles(None), [])

    def test_unknown_role_returns_empty(self):
        self.assertEqual(get_users_for_roles(["_Test WA Nonexistent Role"]), [])


class TestResolvePhone(IntegrationTestCase):
    """Tests for the phone-source priority setting."""

    NUMBERS = {"u@example.com": "9990001111"}

    def test_user_only_ignores_employee(self):
        with patch(
            "frappe_whatsapp.utils.recipients._get_employee_number", return_value="8880002222"
        ) as emp:
            self.assertEqual(
                resolve_phone("u@example.com", SOURCE_USER_ONLY, self.NUMBERS), "9990001111"
            )
            emp.assert_not_called()

    def test_employee_only_ignores_user(self):
        with patch(
            "frappe_whatsapp.utils.recipients._get_employee_number", return_value="8880002222"
        ):
            self.assertEqual(
                resolve_phone("u@example.com", SOURCE_EMPLOYEE_ONLY, self.NUMBERS), "8880002222"
            )

    def test_user_then_employee_prefers_user(self):
        with patch(
            "frappe_whatsapp.utils.recipients._get_employee_number", return_value="8880002222"
        ):
            self.assertEqual(
                resolve_phone("u@example.com", SOURCE_USER_THEN_EMPLOYEE, self.NUMBERS),
                "9990001111",
            )

    def test_user_then_employee_falls_back(self):
        with patch(
            "frappe_whatsapp.utils.recipients._get_employee_number", return_value="8880002222"
        ):
            self.assertEqual(
                resolve_phone("u@example.com", SOURCE_USER_THEN_EMPLOYEE, {}), "8880002222"
            )

    def test_employee_then_user_falls_back(self):
        with patch("frappe_whatsapp.utils.recipients._get_employee_number", return_value=None):
            self.assertEqual(
                resolve_phone("u@example.com", SOURCE_EMPLOYEE_THEN_USER, self.NUMBERS),
                "9990001111",
            )


class TestGetRoleRecipients(IntegrationTestCase):
    """Tests for end-to-end recipient resolution."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for role in (ROLE, OTHER_ROLE):
            if not frappe.db.exists("Role", role):
                frappe.get_doc({"doctype": "Role", "role_name": role}).insert(
                    ignore_permissions=True
                )
        _make_user("wa_one@example.com", "9876543210", [ROLE])
        _make_user("wa_two@example.com", "+91 98765 43211", [ROLE, OTHER_ROLE])
        _make_user("wa_nophone@example.com", None, [ROLE])
        frappe.db.commit()  # nosemgrep: frappe-manual-commit -- test fixture setup

    def _notification(self, rows):
        return frappe._dict(
            name="_Test WA Notification",
            recipients=[frappe._dict(r) for r in rows],
        )

    def test_no_rows_returns_empty(self):
        recipients, skipped = get_role_recipients(frappe._dict(name="x", recipients=[]))
        self.assertEqual(recipients, [])
        self.assertEqual(skipped, [])

    def test_resolves_and_normalizes(self):
        recipients, _ = get_role_recipients(self._notification([{"receiver_by_role": ROLE}]))
        phones = [r["phone"] for r in recipients]
        self.assertIn("919876543210", phones)
        self.assertIn("919876543211", phones)

    def test_user_without_number_is_skipped_not_raised(self):
        recipients, skipped = get_role_recipients(self._notification([{"receiver_by_role": ROLE}]))
        self.assertNotIn("wa_nophone@example.com", [r["user"] for r in recipients])
        self.assertIn("wa_nophone@example.com", [s["user"] for s in skipped])

    def test_two_matching_roles_sends_once(self):
        recipients, _ = get_role_recipients(
            self._notification(
                [{"receiver_by_role": ROLE}, {"receiver_by_role": OTHER_ROLE}]
            )
        )
        phones = [r["phone"] for r in recipients]
        self.assertEqual(len(phones), len(set(phones)))
        self.assertEqual(phones.count("919876543211"), 1)

    def test_row_condition_filters(self):
        doc = frappe.get_doc({"doctype": "User", "name": "Administrator"})
        rows = [{"receiver_by_role": ROLE, "condition": "doc.name == 'nobody'"}]
        recipients, _ = get_role_recipients(self._notification(rows), doc=doc)
        self.assertEqual(recipients, [])

    def test_row_condition_skipped_without_doc(self):
        # Scheduler events have no document, so conditional rows cannot apply.
        rows = [{"receiver_by_role": ROLE, "condition": "doc.name == 'x'"}]
        recipients, _ = get_role_recipients(self._notification(rows), doc=None)
        self.assertEqual(recipients, [])

    def test_bad_condition_is_logged_not_raised(self):
        doc = frappe.get_doc({"doctype": "User", "name": "Administrator"})
        rows = [{"receiver_by_role": ROLE, "condition": "doc.no_such_field.boom"}]
        recipients, _ = get_role_recipients(self._notification(rows), doc=doc)
        self.assertEqual(recipients, [])
