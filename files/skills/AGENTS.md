## Project Overview

This is an **Odoo addon module** in Odoo version is 19. Odoo core can be found from ~/Odoo/src/19/odoo/ and ~/Odoo/src/19/enterprise/

### Rules for developement
* Do not improvise when using the bash tools listed in this file, they are designed to work as is.
* When writing new code, try to keep it as minimal as possible. Each line of code is a liability, thus keeping it minimal and readable is extremely important. KISS = Keep it stupid simple.
* No unspecified fallback logic. Silent failures on unexpected inputs are not OK. I.e. avoid adding `try:except` blocks and for well defined API's use `some_dict[key]` instead of `some_dict.get(key)`.
* For changes with any logic, write automated tests. No need to write tests for adding a field to model and normal view, those get tested automatically when the module loads without errors. If automated tests are expected to raise an error, and the module logs it as an ERROR line, use `mute_logger`:
* Tests should NOT assert translatable terms such as display names or other UI strings, as they loading an Odoo db with another language can cause issues with the test.
* This is a greenfield project, no need to keep backwards compatibility.
* Avoid custom CSS, use bootstrap classes when ever possible.

### Odoo bash tools using the (bodoo) helper:
* Install module: `bodoo 19 install`
* Upgrade module: `bodoo 19 upgrade`
* Run the automated tests: `bodoo 19 tests --no-coverage`. Note! ALWAYS report the amount of tests after the command finishes (odoo tells it in the logs). If the count is zero, try installing the module first.
* Export Finnish translations: `bodoo 19 translate --languages=fi`. Note! Never edit the `msgid` values directly, they should always be exported from Odoo. And do not change existing translations if the term is already translated. NOTE2: If HTML code is being exported to the *.po file, add `t-if="True"` to the html element, this way Odoo will not export the HTML node.
* For manual testing with browser, first start the server `bodoo 19 server --http-port=9999`, then navigate to http://127.0.0.1:9999/web/login and login as admin:admin
