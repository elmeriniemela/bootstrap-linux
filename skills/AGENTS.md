## Project Overview

This is an **Odoo addon module**. Current Odoo Version: 19.0 (main branch)


### Rules for developement
1. Do not improvise when using the bash commands listed in this file, they are designed to work as is.
2. When writing new code, try to keep it as minimal as possible. Each line of code is a liability, thus keeping it minimal and readable is extremely important.
3. If automated tests are expected to raise an error, and the module logs it as an ERROR line, use `mute_logger`:


### Running Automated Tests
```bash
odoobot 19 test.conf tests --no-coverage
# ALWAYS report the amount of tests after the command finishes (odoo tells it in the logs)
```

### Manual testing with browser

1. Start the server
```bash
odoobot 19 test.conf server --http-port=9999
```
2. Navigate to http://127.0.0.1:9999/web/login and login as admin:admin


### Export Finnish translations.
```bash
odoobot 19 test.conf translate --languages=fi
```