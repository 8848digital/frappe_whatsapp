# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

import frappe
from frappe_whatsapp.testing import IntegrationTestCase


class TestWhatsAppSettings(IntegrationTestCase):
    """Tests for WhatsApp Settings doctype."""

    def test_settings_exists(self):
        """Test WhatsApp Settings singleton exists."""
        settings = frappe.get_single("WhatsApp Settings")
        self.assertIsNotNone(settings)

    def test_settings_is_single(self):
        """Test that WhatsApp Settings is a Single doctype."""
        meta = frappe.get_meta("WhatsApp Settings")
        self.assertTrue(meta.issingle)
