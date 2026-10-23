"""Send attachments to Meta as uploaded media instead of links.

A ``link`` makes Meta's servers download the file. That fails for private
files, for sites Meta cannot reach (localhost, VPN, firewall), and for URLs
with a bad query string. Meta still accepts the send, so the failure shows
only later as "Unable to upload the media". Uploading the file to
``/{phone_id}/media`` and sending the returned id avoids all of these.
"""

import mimetypes
from urllib.parse import unquote, urlparse

import frappe
import requests
from frappe import _


def upload_media(whatsapp_account, content, filename, mimetype):
	"""Upload ``content`` to Meta and return the media id."""
	token = whatsapp_account.get_password("token")
	response = requests.post(
		f"{whatsapp_account.url}/{whatsapp_account.version}/{whatsapp_account.phone_id}/media",
		headers={"Authorization": f"Bearer {token}"},
		data={"messaging_product": "whatsapp", "type": mimetype},
		files={"file": (filename, content, mimetype)},
		timeout=60,
	)
	if not response.ok:
		frappe.throw(_("WhatsApp media upload failed: {0}").format(response.text))

	media_id = response.json().get("id")
	if not media_id:
		frappe.throw(_("WhatsApp media upload returned no id: {0}").format(response.text))
	return media_id


def get_local_file(file_url):
	"""Return the File document for ``file_url`` if it is stored on this site."""
	if not file_url:
		return None

	path = file_url
	site_url = frappe.utils.get_url()
	if path.startswith(site_url):
		path = path[len(site_url):]
	elif path.startswith(("http://", "https://")):
		return None

	path = unquote(urlparse(path).path)
	if not path.startswith("/"):
		path = f"/{path}"

	name = frappe.db.get_value("File", {"file_url": path}, "name")
	return frappe.get_doc("File", name) if name else None


def get_absolute_url(file_url):
	if file_url.startswith(("http://", "https://")):
		return file_url
	return frappe.utils.get_url(file_url if file_url.startswith("/") else f"/{file_url}")


def get_media_object(whatsapp_account, file_url, filename=None):
	"""Return the media object for a template header or a media message.

	A file stored on this site is uploaded and sent as ``{"id": ...}``. A file
	hosted elsewhere is sent as ``{"link": ...}``. If the upload of a public
	file fails, the link is used. If the upload of a private file fails, the
	error is raised, because Meta cannot download a private link.

	``filename`` is set on the object when given (document headers only).
	"""
	file_doc = get_local_file(file_url)
	media = None

	if file_doc:
		filename = filename or file_doc.file_name
		mimetype = mimetypes.guess_type(file_doc.file_name or "")[0] or "application/octet-stream"
		try:
			with open(file_doc.get_full_path(), "rb") as f:
				content = f.read()
			media = {"id": upload_media(whatsapp_account, content, file_doc.file_name, mimetype)}
		except Exception:
			if file_doc.is_private:
				raise
			frappe.log_error(title=f"WhatsApp media upload failed, sending link instead: {file_url}")

	if media is None:
		media = {"link": get_absolute_url(file_url)}

	if filename:
		media["filename"] = filename
	return media
