# Development and checks

The root launcher installs dependencies and starts both services:

```sh
python3 dev.py
```

For an isolated preview on different ports:

```sh
python3 dev.py --preview --backend-port 8013 --frontend-port 5176
```

Use one backend worker without auto-reload: demo state and the activity feed live in memory. For IDE startup, use the root `.venv` interpreter, module `app.run`, and `backend` as the working directory. The root launcher also runs Vite and stops both services together.

Setup was verified on macOS. Windows and Linux are untested. LaunchDarkly clients use the default-region endpoints; EU, federal, and custom endpoints are not configured.

## Checks

From the project root:

```sh
APP_MODE=preview AI_ENABLED=false .venv/bin/python -m pytest backend/tests
npm --prefix frontend test
npm --prefix frontend run build
python3 scripts/update_readme.py --check
```

Tests use local doubles and do not generate paid model calls.

## Code reference maintenance

Application source contains `DEMO START` and `DEMO END` comments identifying complete feature blocks and their purpose. After source edits, refresh the README's line references and the full implementation map:

```sh
python3 scripts/update_readme.py
```

`scripts/readme_sections.json` associates guide paragraphs with source blocks. Update its anchor when editing a referenced paragraph. The check rejects stale ranges, missing images, and external README links outside LaunchDarkly documentation.

## Trigger validation

Check the local trigger configuration without changing the flag:

```sh
PYTHONPATH=backend .venv/bin/python -m app.remediate --check
```

The same command without `--check` fires the configured OFF trigger. Do not retry a timeout without checking the flag's state first.

## Supporting material

- [Implementation map](code-map.md)
- [Setup and incident walkthrough](../README.md)

Screenshots combine configuration forms and recorded outcomes. Forms opened during README capture were discarded without saving account changes. Recorded results illustrate the demonstrated flow; they do not guarantee identical data in another account.
