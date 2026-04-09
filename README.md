# Finance Enforcer

An MCP-powered agent that reads a Tiller Money Google Sheet and enforces budgeting rules via the Sheets API. Phase 1 provides scaffolding and service-account authentication against the Tiller sheet.

## Smoke test

```bash
# activate the venv
source .venv/bin/activate

# run the smoke test (prints sheet title + tab names)
python tests/smoke_test.py
```
