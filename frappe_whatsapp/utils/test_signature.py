# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

import hashlib
import hmac
import json
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.utils.password import set_encrypted_password

from frappe_whatsapp.testing import IntegrationTestCase
from frappe_whatsapp.utils import webhook
from frappe_whatsapp.utils.signature import REQUIRE_SIGNED_KEY, signature_matches

SECRET = "test_app_secret_123"
ACCOUNT = "Test WA Signature Account"
BODY = b'{"entry": [{"changes": [{"value": {"messages": []}}]}]}'


def sign(body, secret=SECRET):
	return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestSignatureMatches(unittest.TestCase):
	"""Checks of the HMAC comparison only, no database."""

	def test_valid_signature(self):
		self.assertTrue(signature_matches(BODY, sign(BODY), [SECRET]))

	def test_uppercase_hex(self):
		self.assertTrue(
			signature_matches(BODY, sign(BODY).upper().replace("SHA256=", "sha256="), [SECRET])
		)

	def test_str_body(self):
		self.assertTrue(signature_matches(BODY.decode(), sign(BODY), [SECRET]))

	def test_wrong_secret(self):
		self.assertFalse(signature_matches(BODY, sign(BODY, "other"), [SECRET]))

	def test_tampered_body(self):
		self.assertFalse(signature_matches(BODY + b" ", sign(BODY), [SECRET]))

	def test_missing_or_malformed_header(self):
		for header in (None, "", "abc", "sha1=" + "0" * 40):
			self.assertFalse(signature_matches(BODY, header, [SECRET]))

	def test_any_of_several_secrets(self):
		self.assertTrue(signature_matches(BODY, sign(BODY, "second"), ["first", "second"]))


class TestWebhookSignature(IntegrationTestCase):
	"""The webhook POST handler refuses unsigned calls when an App Secret is set."""

	def setUp(self):
		if not frappe.db.exists("WhatsApp Account", ACCOUNT):
			frappe.get_doc(
				{
					"doctype": "WhatsApp Account",
					"account_name": ACCOUNT,
					"status": "Active",
					"url": "https://graph.facebook.com",
					"version": "v17.0",
					"phone_id": "signature_test_phone_id",
					"webhook_verify_token": "signature_test_verify_token",
				}
			).insert(ignore_permissions=True)
		set_encrypted_password("WhatsApp Account", ACCOUNT, "token_value", "token")
		self.addCleanup(frappe.conf.pop, REQUIRE_SIGNED_KEY, None)

	def tearDown(self):
		frappe.db.rollback()

	def set_secret(self, secret):
		if secret:
			set_encrypted_password("WhatsApp Account", ACCOUNT, secret, "app_secret")
		else:
			frappe.db.delete("__Auth", {"doctype": "WhatsApp Account", "fieldname": "app_secret"})

	def post(self, body=BODY, header=None):
		request = MagicMock()
		request.method = "POST"
		request.get_data.return_value = body
		request.headers = {"X-Hub-Signature-256": header} if header else {}
		frappe.local.form_dict = frappe._dict(json.loads(body))
		logs_before = frappe.db.count("WhatsApp Notification Log")
		with patch("frappe.request", request, create=True):
			response = webhook.webhook()
		return response, frappe.db.count("WhatsApp Notification Log") - logs_before

	def test_no_secret_accepts_unsigned(self):
		self.set_secret(None)
		response, new_logs = self.post()
		self.assertIsNone(response)
		self.assertEqual(new_logs, 1)

	def test_no_secret_strict_mode_refuses(self):
		self.set_secret(None)
		frappe.conf[REQUIRE_SIGNED_KEY] = 1
		response, new_logs = self.post()
		self.assertEqual(response.status_code, 403)
		self.assertEqual(new_logs, 0)

	def test_secret_refuses_unsigned(self):
		self.set_secret(SECRET)
		response, new_logs = self.post()
		self.assertEqual(response.status_code, 403)
		self.assertEqual(new_logs, 0)

	def test_secret_refuses_forged(self):
		self.set_secret(SECRET)
		response, new_logs = self.post(header=sign(BODY, "forged"))
		self.assertEqual(response.status_code, 403)
		self.assertEqual(new_logs, 0)

	def test_secret_accepts_signed(self):
		self.set_secret(SECRET)
		response, new_logs = self.post(header=sign(BODY))
		self.assertIsNone(response)
		self.assertEqual(new_logs, 1)

	def test_inactive_account_secret_is_ignored(self):
		self.set_secret(SECRET)
		frappe.db.set_value("WhatsApp Account", ACCOUNT, "status", "Inactive")
		response, new_logs = self.post()
		self.assertIsNone(response)
		self.assertEqual(new_logs, 1)
