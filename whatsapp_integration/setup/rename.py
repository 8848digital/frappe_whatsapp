# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Move a site from the old package name ``frappe_whatsapp`` to ``whatsapp_integration``.

Run once per site, after the new app is on the bench and before ``migrate``::

    echo "from whatsapp_integration.setup.rename import migrate_from_frappe_whatsapp; migrate_from_frappe_whatsapp()" \
        | bench --site <site> console
    bench --site <site> migrate

``bench execute`` cannot run it: Frappe does not run code of an app that the
site does not have installed yet. It is not a bench command either, because
``commands/__init__.py`` is overwritten by ``scripts/sync_skills.sh``. It is
safe to run again: when nothing is left to rename, it does nothing.
"""

import json

import frappe

OLD_APP = "frappe_whatsapp"
NEW_APP = "whatsapp_integration"
OLD_MODULE = "Frappe Whatsapp"
NEW_MODULE = "WhatsApp Integration"


def migrate_from_frappe_whatsapp():
	"""Rename the app and its module in the site database, then commit."""
	rename_installed_app()
	rename_module()
	rename_method_paths()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- run by hand through bench execute
	frappe.clear_cache()
	print(f"Site {frappe.local.site}: {OLD_APP} renamed to {NEW_APP}. Now run bench migrate.")


def rename_installed_app():
	installed = json.loads(frappe.db.get_global("installed_apps") or "[]")
	if OLD_APP in installed:
		installed = [NEW_APP if app == OLD_APP else app for app in installed]
		# Drop a duplicate when the new app was also installed.
		installed = list(dict.fromkeys(installed))
		frappe.db.set_global("installed_apps", json.dumps(installed))

	frappe.db.delete("Installed Application", {"app_name": OLD_APP})


def rename_module():
	"""Rename the Module Def and every Link to it (DocType, Report, Custom Field...)."""
	if not frappe.db.exists("Module Def", OLD_MODULE):
		return

	if frappe.db.exists("Module Def", NEW_MODULE):
		frappe.delete_doc("Module Def", NEW_MODULE, force=True, ignore_permissions=True)

	frappe.rename_doc("Module Def", OLD_MODULE, NEW_MODULE, force=True, show_alert=False)
	frappe.db.set_value("Module Def", NEW_MODULE, "app_name", NEW_APP)


def rename_method_paths():
	"""Point patch logs and scheduled jobs at the new package.

	Without this, migrate runs the old patches again under their new names.
	"""
	old_prefix = f"{OLD_APP}."
	new_prefix = f"{NEW_APP}."

	for doctype, field in (("Patch Log", "patch"), ("Scheduled Job Type", "method")):
		table = frappe.qb.DocType(doctype)
		column = table[field]
		rows = (
			frappe.qb.from_(table)
			.select(table.name, column)
			.where(column.like(f"{old_prefix}%"))
			.run(as_dict=True)
		)
		for row in rows:
			new_value = new_prefix + row[field][len(old_prefix) :]
			new_value = new_value.replace(f".{OLD_APP}.", f".{NEW_APP}.")
			frappe.qb.update(table).set(column, new_value).where(table.name == row.name).run()
