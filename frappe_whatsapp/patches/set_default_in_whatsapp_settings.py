# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

import frappe

def execute():
    settings = frappe.get_single("WhatsApp Settings")
    settings.allow_auto_read_receipt = 1
    settings.save()