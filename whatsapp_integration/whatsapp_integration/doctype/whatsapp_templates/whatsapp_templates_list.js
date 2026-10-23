// Copyright (c) 2026 8848 Digital LLP. All rights reserved.
// Proprietary and confidential. Unauthorized copying, distribution, or use
// of this file, via any medium, is strictly prohibited without prior
// written permission from 8848 Digital LLP.

frappe.listview_settings['WhatsApp Templates'] = {

	onload: function(listview) {
		listview.page.add_inner_button(__("Sync from Meta"), function() {
			frappe.call({
				method: 'whatsapp_integration.whatsapp_integration.doctype.whatsapp_templates.whatsapp_templates.fetch',
				freeze: true,
				freeze_message: __("Syncing templates from Meta..."),
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Sync Complete"),
							message: r.message,
							indicator: "green"
						});
						listview.refresh();
					}
				}
			});
		});
	}
};