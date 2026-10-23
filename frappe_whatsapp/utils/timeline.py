"""Show WhatsApp messages in the timeline of the document they belong to."""

import frappe
from frappe import _
from frappe.utils import escape_html, strip_html_tags

TIMELINE_LIMIT = 50
MAX_PREVIEW_LENGTH = 300


def get_whatsapp_timeline(doctype, docname):
	"""Return timeline items for WhatsApp Messages linked to the document.

	Registered for every doctype through the ``additional_timeline_content``
	hook. Uses the (reference_doctype, reference_name) index of WhatsApp
	Message, so it costs one indexed query per form load.
	"""
	if doctype == "WhatsApp Message":
		return []
	if not frappe.has_permission("WhatsApp Message", "read"):
		return []

	messages = frappe.get_all(
		"WhatsApp Message",
		filters={"reference_doctype": doctype, "reference_name": docname},
		fields=[
			"name", "type", "to", "from", "message", "content_type",
			"template", "status", "creation", "owner",
		],
		order_by="creation desc",
		limit=TIMELINE_LIMIT,
	)
	return [get_timeline_item(message) for message in messages]


def get_timeline_item(message):
	if message.type == "Incoming":
		title = _("WhatsApp received from {0}").format(escape_html(message["from"] or ""))
	else:
		title = _("WhatsApp sent to {0}").format(escape_html(message.to or ""))

	if message.template:
		body = _("Template: {0}").format(escape_html(message.template))
	else:
		text = strip_html_tags(message.message or "").strip()
		if len(text) > MAX_PREVIEW_LENGTH:
			text = text[:MAX_PREVIEW_LENGTH] + "…"
		body = escape_html(text) or escape_html(message.content_type or "")

	status = f' · <span class="text-muted">{escape_html(message.status)}</span>' if message.status else ""
	link = frappe.utils.get_link_to_form("WhatsApp Message", message.name, title)

	return {
		"icon": "message",
		"is_card": True,
		"creation": message.creation,
		"content": f"<div>{link}{status}</div><div class='text-muted small'>{body}</div>",
	}
