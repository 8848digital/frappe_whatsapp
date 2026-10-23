# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

from whatsapp_integration.setup.rename import migrate_from_frappe_whatsapp_command

from .export_fixtures import export_fixtures

commands = [export_fixtures, migrate_from_frappe_whatsapp_command]
