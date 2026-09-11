# Upgrade to LoopCheck 0.5.0

Stop the old LoopCheck service before replacing application files. Preserve `.env` and the entire `data/app` directory. Install the current `requirements.txt` and start `run.py` as usual. Do not point test processes at live data; use `LOOPCHECK_DATA` with a separate directory.

On startup, projects with legacy flow-only contracts trigger a SQLite backup named `pre-v05-<timestamp>.sqlite3` beside the database. SQLite's backup API includes committed WAL data. Each original flow becomes a stable business requirement with revision 1 and its existing check. Old contracts, runs, screenshots and cost records remain available. Projects stop watching until explicitly re-enabled. The first 0.5 run establishes fresh current evidence; old passing runs do not approve migrated requirements.

Business requirements and checks now have separate lifecycles. A requirement can have no flow. Editing its expectation or rebuilding its check increments its revision and clears the binding. Retirement requires a reason, keeps history and frees an active slot. Restoration increments the revision and immediately rechecks any retained flow after human confirmation. An immutable contract captures the reviewed set. Pass history uses requirement ID, revision and flow digest, never title alone.

Every mutation creates a draft. Confirmation verifies the draft digest, parent contract and current source hash. MCP has no confirmation, retirement, restoration or revision tool. Drafts from 0.4 must be prepared again.

Result clients must handle `incomplete`. It means the scope is empty or some active requirements lack confirmed checks despite executable flows completing. Use `can_accept` from the latest API response; never infer approval from a cached `state: passed`. `is_current` compares source, contract and latest check. Starting another check invalidates the previous result's currentness. Historical raw outcomes stay unchanged.

Rollback: stop 0.5, preserve its database and artifacts separately, restore the pre-upgrade SQLite backup as `loopcheck.sqlite3` into a separate data directory, and run 0.4 against that directory. Never copy over an open SQLite database or combine an older database with newer WAL files. New 0.5 changes are not represented in the pre-upgrade backup.

Scope: loopback HTTP previews only; trusted local frontend projects. No login, payment, arbitrary commands or backend test orchestration. Exploration is limited to three fresh observations, six actions per path, the selected origin, and the existing browser deadline. Public mode is bundled-sample-only.
