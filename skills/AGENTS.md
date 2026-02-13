## Project Overview

This is an **Odoo addon module**. Do not improvise when using the bash commands listed in this file, they are designed to work as is.

**Current Odoo Version**: 19.0 (main branch)

### Running Automated Tests
```bash
source activate odoo19 test.conf && odoo --test-enable -u $ODOO_MODULE --stop-after-init --http-port=0
# ALWAYS report the amount of tests after the command finishes (odoo tells it in the logs)
```

### Manual testing with browser

1. Start the server
```bash
source activate odoo19 test.conf && odoo -u $ODOO_MODULE --http-port=9999
```
2. Navigate to http://127.0.0.1:9999/web/login and login as admin:admin


### Export Finnish translations.
```bash
source activate odoo19 test.conf && odoo i18n export $ODOO_MODULE --languages=fi
```