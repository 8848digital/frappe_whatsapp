# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

import json
from unittest.mock import MagicMock, patch

import frappe

from frappe_whatsapp.testing import IntegrationTestCase
from frappe_whatsapp.utils.media import get_local_file, get_media_object

ACCOUNT = "Test WA Media Account"
TEMPLATE = "test_media_doc_template-en"
MEDIA_POST = "frappe_whatsapp.utils.media.requests.post"
NOTIFY_POST = (
	"frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_notification."
	"whatsapp_notification.make_post_request"
)


def upload_ok(media_id="media-123"):
	response = MagicMock(ok=True)
	response.json.return_value = {"id": media_id}
	return MagicMock(return_value=response)


def upload_fails():
	return MagicMock(return_value=MagicMock(ok=False, text="boom"))


class TestMedia(IntegrationTestCase):
	"""Attachments are uploaded to Meta and sent as a media id."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("WhatsApp Account", ACCOUNT):
			frappe.get_doc(
				{
					"doctype": "WhatsApp Account",
					"account_name": ACCOUNT,
					"status": "Active",
					"url": "https://graph.facebook.com",
					"version": "v17.0",
					"phone_id": "media_test_phone_id",
					"webhook_verify_token": "media_test_verify_token",
				}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("WhatsApp Templates", TEMPLATE):
			frappe.get_doc(
				{
					"doctype": "WhatsApp Templates",
					"template_name": "test_media_doc_template",
					"actual_name": "test_media_doc_template",
					"template": "Your invoice is attached",
					"category": "UTILITY",
					"language": frappe.db.get_value("Language", {"language_code": "en"}) or "en",
					"language_code": "en",
					"whatsapp_account": ACCOUNT,
					"status": "APPROVED",
					"id": "test_media_doc_template_id",
					"header_type": "DOCUMENT",
				}
			).db_insert()
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- test fixture must be visible to later queries

	def setUp(self):
		frappe.utils.password.set_encrypted_password("WhatsApp Account", ACCOUNT, "token_value", "token")
		self.account = frappe.get_doc("WhatsApp Account", ACCOUNT)

	def tearDown(self):
		frappe.db.rollback()

	def make_file(self, is_private=0, name="invoice.pdf"):
		return frappe.get_doc(
			{
				"doctype": "File",
				"file_name": name,
				"content": b"%PDF-1.4 test",
				"is_private": is_private,
			}
		).insert(ignore_permissions=True)

	def test_get_local_file_resolves_relative_and_absolute_urls(self):
		file_doc = self.make_file()
		self.assertEqual(get_local_file(file_doc.file_url).name, file_doc.name)
		self.assertEqual(get_local_file(frappe.utils.get_url(file_doc.file_url)).name, file_doc.name)
		self.assertIsNone(get_local_file("https://example.com/x.pdf"))
		self.assertIsNone(get_local_file("/files/does-not-exist.pdf"))

	def test_public_file_is_uploaded(self):
		file_doc = self.make_file()
		with patch(MEDIA_POST, upload_ok()) as post:
			media = get_media_object(self.account, file_doc.file_url, "Invoice.pdf")
		self.assertEqual(media, {"id": "media-123", "filename": "Invoice.pdf"})
		self.assertIn("/media_test_phone_id/media", post.call_args.args[0])
		self.assertEqual(post.call_args.kwargs["files"]["file"][2], "application/pdf")

	def test_private_file_is_uploaded(self):
		file_doc = self.make_file(is_private=1)
		with patch(MEDIA_POST, upload_ok()):
			media = get_media_object(self.account, file_doc.file_url)
		self.assertEqual(media, {"id": "media-123", "filename": file_doc.file_name})

	def test_external_url_is_sent_as_link(self):
		with patch(MEDIA_POST) as post:
			media = get_media_object(self.account, "https://example.com/a.jpg")
		post.assert_not_called()
		self.assertEqual(media, {"link": "https://example.com/a.jpg"})

	def test_failed_upload_of_public_file_falls_back_to_link(self):
		file_doc = self.make_file()
		with patch(MEDIA_POST, upload_fails()):
			media = get_media_object(self.account, file_doc.file_url)
		self.assertEqual(media["link"], frappe.utils.get_url(file_doc.file_url))

	def test_failed_upload_of_private_file_raises(self):
		file_doc = self.make_file(is_private=1)
		with patch(MEDIA_POST, upload_fails()), self.assertRaises(frappe.ValidationError):
			get_media_object(self.account, file_doc.file_url)

	def test_notification_attach_from_field_sends_media_id(self):
		"""Forum report: Attach from field failed with "Unable to upload the media"."""
		file_doc = self.make_file(is_private=1)
		frappe.db.set_value("User", "Administrator", "user_image", file_doc.file_url)
		notification = frappe.get_doc(
			{
				"doctype": "WhatsApp Notification",
				"notification_name": "Test media notification",
				"notification_type": "DocType Event",
				"reference_doctype": "User",
				"doctype_event": "On Update",
				"template": TEMPLATE,
				"whatsapp_account": ACCOUNT,
				"custom_attachment": 1,
				"attach_from_field": "user_image",
				"file_name": "Invoice.pdf",
			}
		)
		user = frappe.get_doc("User", "Administrator")

		with patch(MEDIA_POST, upload_ok("media-999")), patch(NOTIFY_POST) as notify_post:
			notify_post.return_value = {"messages": [{"id": "wamid.media_test"}]}
			frappe.flags.integration_request = MagicMock()
			frappe.flags.integration_request.json.return_value = notify_post.return_value
			notification.send_template_message(user, phone_no="919900000001")

		sent = json.loads(notify_post.call_args.kwargs["data"])
		header = next(c for c in sent["template"]["components"] if c["type"] == "header")
		self.assertEqual(
			header["parameters"][0],
			{"type": "document", "document": {"id": "media-999", "filename": "Invoice.pdf"}},
		)
