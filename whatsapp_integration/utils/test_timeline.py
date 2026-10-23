# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

from unittest.mock import patch

import frappe
from frappe.desk.form.load import get_additional_timeline_content

from whatsapp_integration.testing import IntegrationTestCase
from whatsapp_integration.utils.timeline import MAX_PREVIEW_LENGTH, get_whatsapp_timeline

ACCOUNT = "Test WA Timeline Account"


class TestWhatsAppTimeline(IntegrationTestCase):
	"""Linked WhatsApp Messages appear in the document timeline."""

	def setUp(self):
		if not frappe.db.exists("WhatsApp Account", ACCOUNT):
			frappe.get_doc({
				"doctype": "WhatsApp Account",
				"account_name": ACCOUNT,
				"status": "Active",
				"url": "https://graph.facebook.com",
				"version": "v17.0",
				"phone_id": "timeline_test_phone_id",
				"webhook_verify_token": "timeline_test_verify_token",
			}).insert(ignore_permissions=True)
		self.role = frappe.get_doc({"doctype": "Role", "role_name": "Test WA Timeline Role"})
		if not frappe.db.exists("Role", self.role.role_name):
			self.role.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def add_message(self, message, msg_type="Incoming", **kwargs):
		# Incoming messages are not sent to Meta, so no API call is made.
		return frappe.get_doc(dict({
			"doctype": "WhatsApp Message",
			"type": msg_type,
			"from": "919900000003",
			"message": message,
			"content_type": "text",
			"reference_doctype": "Role",
			"reference_name": self.role.name,
			"whatsapp_account": ACCOUNT,
		}, **kwargs)).insert(ignore_permissions=True)

	def test_linked_messages_are_returned_newest_first(self):
		first = self.add_message("first")
		second = self.add_message("second")
		frappe.db.set_value("WhatsApp Message", first.name, "creation", "2020-01-01 00:00:00")

		items = get_whatsapp_timeline("Role", self.role.name)

		self.assertEqual(len(items), 2)
		self.assertIn(second.name, items[0]["content"])
		self.assertIn("second", items[0]["content"])
		self.assertTrue(items[0]["is_card"])
		self.assertEqual(items[0]["icon"], "message")

	def test_hook_is_registered(self):
		message = self.add_message("from hook")
		contents = get_additional_timeline_content("Role", self.role.name)
		self.assertTrue(any(message.name in item["content"] for item in contents))

	def test_message_text_is_escaped(self):
		self.add_message("<img src=x onerror=alert(1)>hello")
		content = get_whatsapp_timeline("Role", self.role.name)[0]["content"]
		self.assertNotIn("<img", content)
		self.assertIn("hello", content)

	def test_long_message_is_truncated(self):
		self.add_message("a" * (MAX_PREVIEW_LENGTH + 50))
		content = get_whatsapp_timeline("Role", self.role.name)[0]["content"]
		self.assertIn("a" * MAX_PREVIEW_LENGTH + "…", content)
		self.assertNotIn("a" * (MAX_PREVIEW_LENGTH + 1), content)

	def test_template_message_shows_template(self):
		message = self.add_message("ignored")
		# Set directly: inserting a template message would call Meta.
		frappe.db.set_value("WhatsApp Message", message.name, "template", "some_template")
		item = get_whatsapp_timeline("Role", self.role.name)[0]
		self.assertIn("Template: some_template", item["content"])

	def test_other_documents_are_not_included(self):
		self.add_message("elsewhere", reference_name="System Manager")
		self.assertEqual(get_whatsapp_timeline("Role", self.role.name), [])

	def test_no_read_permission_returns_nothing(self):
		self.add_message("secret")
		with patch("whatsapp_integration.utils.timeline.frappe.has_permission", return_value=False):
			self.assertEqual(get_whatsapp_timeline("Role", self.role.name), [])

	def test_whatsapp_message_form_is_skipped(self):
		message = self.add_message("self")
		self.assertEqual(get_whatsapp_timeline("WhatsApp Message", message.name), [])

