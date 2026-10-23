# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

import json
import os
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def after_migrate():
	create_custom_fields()


def create_custom_fields():
	CUSTOM_FIELDS = {}
	print("Creating/Updating Custom Fields....")
	path = os.path.join(os.path.dirname(__file__), "whatsapp_integration/custom_fields")
	for file in os.listdir(path):
		with open(os.path.join(path, file)) as f:
			CUSTOM_FIELDS.update(json.load(f))
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
