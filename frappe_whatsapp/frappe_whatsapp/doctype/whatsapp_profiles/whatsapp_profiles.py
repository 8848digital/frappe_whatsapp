# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

import frappe
from frappe.model.document import Document
from frappe_whatsapp.utils import format_number

class WhatsAppProfiles(Document):
    def validate(self):
        self.format_whatsapp_number()
        self.set_title()

    def format_whatsapp_number(self):
        if self.number:
            self.number = format_number(self.number)

    def set_title(self):
        self.title = " - ".join(p for p in (self.profile_name, self.number) if p) or "Unnamed Profile"
