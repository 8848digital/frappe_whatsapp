import frappe


def execute():
	"""
	Index WhatsApp Message.message_id.

	The webhook finds a message by message_id on every status update. The column
	had no index, so each lookup walked the whole table through the modified index.
	The field also has search_index set in the DocType, so a later migrate keeps
	the index. Query results do not change.

	Returns:
	    None
	"""
	frappe.db.add_index("WhatsApp Message", ["message_id"])
