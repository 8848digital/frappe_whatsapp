"""Verify that a webhook request came from Meta.

Meta signs every webhook POST with the App Secret of the Meta app. The
``X-Hub-Signature-256`` header holds ``sha256=`` + the hex HMAC-SHA256 of the
raw request body.

The webhook and Flow endpoints are guest endpoints. Without this check, anyone
who knows the URL can create WhatsApp Messages and Notification Logs.

Rules:

- If an active WhatsApp Account has an App Secret, every POST must carry a
  signature that matches one of the configured secrets.
- If no active account has an App Secret, the request is accepted and a
  warning is logged, so existing sites keep working until the secret is set.
  Set site config ``whatsapp_require_signed_webhooks: 1`` to refuse these
  requests too.
"""

import hashlib
import hmac

import frappe
from frappe.utils.password import get_decrypted_password
from werkzeug.wrappers import Response

SIGNATURE_HEADER = "X-Hub-Signature-256"
SIGNATURE_PREFIX = "sha256="
REQUIRE_SIGNED_KEY = "whatsapp_require_signed_webhooks"


def signature_matches(body, header, secrets):
	"""Return True if ``header`` is a valid signature of ``body`` for one of ``secrets``."""
	if not header or not header.startswith(SIGNATURE_PREFIX):
		return False

	received = header[len(SIGNATURE_PREFIX):].strip().lower()
	if isinstance(body, str):
		body = body.encode()

	for secret in secrets:
		expected = hmac.new(secret.encode(), body or b"", hashlib.sha256).hexdigest()
		if hmac.compare_digest(received, expected):
			return True
	return False


def get_app_secrets():
	"""Return the App Secrets of all active WhatsApp Accounts that have one."""
	secrets = []
	for name in frappe.get_all("WhatsApp Account", filters={"status": "Active"}, pluck="name"):
		secret = get_decrypted_password("WhatsApp Account", name, "app_secret", raise_exception=False)
		if secret:
			secrets.append(secret)
	return secrets


def is_verified_meta_request():
	"""Check the signature of the current request.

	This function does not write to the database, so forged requests cannot
	fill it.
	"""
	secrets = get_app_secrets()
	if not secrets:
		if frappe.conf.get(REQUIRE_SIGNED_KEY):
			return False
		frappe.logger("whatsapp").warning(
			"WhatsApp webhook accepted without signature check: no active WhatsApp "
			"Account has an App Secret."
		)
		return True

	body = frappe.request.get_data(cache=True)
	return signature_matches(body, frappe.request.headers.get(SIGNATURE_HEADER), secrets)


def forbidden():
	"""Response for a request that failed the signature check."""
	return Response("Invalid or missing X-Hub-Signature-256", status=403)
