## Project Overview

This is an **Odoo addon module**. Current Odoo Version: 19.0 (main branch)


### Rules for developement
1. Do not improvise when using the bash commands listed in this file, they are designed to work as is.
2. When writing new code, try to keep it as minimal as possible. Each line of code is a liability, thus keeping it minimal and readable is extremely important.
3. No unspecified fallback logic. Silent failures on unexpected inputs are not OK. I.e. avoid adding `try:except` blocks and for well defined API's use `some_dict[key]` instead of `some_dict.get(key)`.
4. If automated tests are expected to raise an error, and the module logs it as an ERROR line, use `mute_logger`:


### Useful bash commands:
1. Install module: `odoobot 19 test.conf install`
2. Run the automated tests: `odoobot 19 test.conf tests --no-coverage`. Note! ALWAYS report the amount of tests after the command finishes (odoo tells it in the logs). If the count is zero, try installing the module first.
3. Export Finnish translations: `odoobot 19 test.conf translate --languages=fi`. Note! Never edit the `msgid` values directly, they should always be imported from Odoo. And do not change existing translations if the term is already translated.
4. For manual testing with browser, first start the server `odoobot 19 test.conf server --http-port=9999`, then navigate to http://127.0.0.1:9999/web/login and login as admin:admin
