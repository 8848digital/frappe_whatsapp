<!--
Copyright (c) 2026 8848 Digital LLP. All rights reserved.
Proprietary and confidential. Unauthorized copying, distribution, or use
of this file, via any medium, is strictly prohibited without prior
written permission from 8848 Digital LLP.
-->

# WhatsApp Integration

A Frappe app that sends and receives WhatsApp messages through the Meta
WhatsApp Cloud API. No third-party gateway is necessary.

Supported Frappe versions: 14, 15 and 16.

## Features

- **Accounts:** connect one or more WhatsApp Business accounts. Set a
  default account for incoming and for outgoing messages.
- **Messages:** send and receive text, media, reactions, interactive
  buttons and lists, and WhatsApp Flows.
- **Templates:** create templates, send them to Meta for approval, and
  sync them from Meta.
- **Notifications:** send a template when a document event or a schedule
  occurs. Map template parameters to document fields, add a condition,
  attach a document print in a print format that you select, or attach a
  file. Send to a phone field, to users with a role, or to both.
- **Bulk messages:** send a template to a recipient list, now or at a
  scheduled time. See the progress and retry the failed messages.
- **Timeline:** WhatsApp messages linked to a document show in the
  timeline of that document.
- **Webhook:** receive incoming messages, delivery status and template
  status from Meta. Requests are checked against the Meta App Secret.

## Install

```bash
bench get-app https://github.com/8848digital/frappe_whatsapp
bench --site <site> install-app whatsapp_integration
bench --site <site> migrate
```

## Set up

1. Create a Meta app with the WhatsApp product. See
   [Get started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started).
2. In Frappe, open **WhatsApp Account** and create an account. Enter the
   access token, URL (`https://graph.facebook.com`), API version, phone
   number ID, business account ID, app ID, a webhook verify token, and the
   **App Secret** (Meta App Dashboard > App settings > Basic).
3. On the account, click **Subscribe App to Webhooks**.
4. In the Meta App Dashboard, set the webhook:
   - **Callback URL:** `https://<site>/api/method/whatsapp_integration.utils.webhook.webhook`
   - **Verify token:** the webhook verify token from step 2
   - **Fields:** `messages` and `message_template_status_update`
5. Create templates in **WhatsApp Templates**, or click **Sync from Meta**
   in the list view.

### Webhook signature

When an active WhatsApp Account has an App Secret, each webhook and Flow
request must have a valid `X-Hub-Signature-256` header. Other requests get
HTTP 403 and nothing is saved.

If no account has an App Secret, requests are accepted and a warning is
logged. To refuse them too, set this site config value:

```bash
bench --site <site> set-config whatsapp_require_signed_webhooks 1
```

## Notifications

Open **WhatsApp Notification** and set:

- **Notification Type:** DocType Event or Scheduler Event.
- **Reference Document Type** and the event, for example After Save or
  Days Before a date field.
- **Template**, and the document fields for the template parameters.
- **Recipients:** a phone field on the document (**Field Name**), roles
  in **Recipients by Role**, or both.
- **Condition** (optional): a Python expression, for example
  `doc.status == "Paid"`.

To attach a PDF of the document, set **Attach Document Print** and,
optionally, a **Print Format**. If **Print Format** is empty, the default
print format of the doctype is used. To send a different print format for
different cases (for example Paid and Partly Paid), make one notification
for each case, each with its print format and condition.

To attach a file, set **Custom Attachment**. Then attach a file in
**Attach**, or enter an Attach field of the document in **Attach from
field**. The file is uploaded to Meta and sent as a media ID, so private
files and sites that Meta cannot reach also work.

## Bulk messages

Open **Bulk WhatsApp Message**. Add recipients one by one, or select a
**WhatsApp Recipient List** (you can import a list from any doctype).
Select a template and set the values for its variables. To send later,
set **Scheduled Time**. The campaign stays in the Scheduled status until
that time.

## Send a template from code

```python
doc.set("_data_list", [
    {"name": "SINV-0001", "phone_no": "+919900000000"},
])
```

## Move a site from frappe_whatsapp

Before version 2, this app had the package name `frappe_whatsapp`. To
move a site that has the old app:

1. Get the new app on the bench, then remove the old app folder from
   `apps/` and from `sites/apps.txt`.
2. Run the rename once for each site, then migrate. The command is safe
   to run again.

   ```bash
   bench --site <site> migrate-from-frappe-whatsapp
   bench --site <site> migrate
   bench build --app whatsapp_integration
   ```

The old webhook and Flow URLs (`/api/method/frappe_whatsapp...`) continue
to work, so you do not have to change them in Meta immediately. Change
them to the new URLs when you can.

## Tests

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app whatsapp_integration
```

## License

Proprietary — Copyright (c) 2026 8848 Digital LLP. All rights reserved.
See [license.txt](license.txt) for details, including the third-party
notice.
