## Project Overview

This is an **Odoo addon module**. Do not improvise when using the bash commands listed in this file, they are designed to work as is.

When writing new code, try to keep it as minimal as possible. Each line of code is a liability, thus keeping it minimal and readable is extremely important.

If automated tests are expected to raise an error, and the module logs it as an ERROR line, use mute_logger:
```python
from odoo.tools import mute_logger
class TestConstraint(TransactionCase):
    def test_uniq_constraint(self):
        self._create_record('one', 'dup-record-gid')
        with self.assertRaises(UniqueViolation), mute_logger('odoo.sql_db'):
            self._create_record('two', 'dup-record-gid')
```

**Current Odoo Version**: 19.0 (main branch)

### Running Automated Tests
```bash
odoobot 19 test.conf tests
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