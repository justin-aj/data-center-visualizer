---
inclusion: always
---

# Parallel Development Protocol

Two people build this project at the same time, each with their own Kiro agents. Each person owns one **lane**. The Spec is in `.kiro/specs/data-center-visualizer/`: implement from `tasks.md`, following `design.md` and `requirements.md`.

## Trigger

When the user says **"start development"**, **"continue development"**, or **"next task"**, run this procedure from step 1. Don't ask for anything the procedure can work out itself.

## 1. Identify the lane

1. If `.kiro/settings/lane` exists (ignored by Git), its content (`A` or `B`) decides the lane.
2. Otherwise, read `git config user.name` and compare it case-insensitively:
   - contains `ajin` → **Lane A: data pipeline**, tasks 1–5
   - contains `sushma` → **Lane B: web app**, tasks 6–9, then integration task 10
3. Otherwise, ask once: "Are you Lane A (data pipeline) or Lane B (web app)?"

Write the result to `.kiro/settings/lane` (create `.kiro/settings/` if needed) so later sessions skip this step. Say which lane was selected in your first message.

## 2. Sync safely

1. Make sure you are on `main`. If you are on another branch and the tree is clean, run `git switch main`. If that fails (for example, `main` is checked out in another worktree), stop and tell the user.
2. If the working tree has uncommitted changes you did not make in this session, stop and ask. Never stash, reset, or discard them.
3. Run `git pull --rebase origin main`.
4. Compare the newest version in `contracts/CHANGELOG.md` with `.kiro/settings/contract-seen`. Read every newer entry, adapt your lane to it, then write the newest version to `contract-seen`.

## 3. Bootstrap the environment (idempotent)

- **Lane A:** needs `uv`. If it is missing, ask before installing it (`brew install uv`). Once `pipeline/` exists, run `uv sync --project pipeline`.
- **Lane B:** needs Node 20 or newer. Once `web/package-lock.json` exists, run `npm ci --prefix web`. Before the first e2e run, run `npx --prefix web playwright install chromium webkit`.
- Both lanes: once `scripts/check-all.sh` exists, run it and note the baseline. If it already fails before you change anything, report it, and fix it only if the failing files belong to your lane.

## 4. Choose work

1. In `tasks.md`, look only at your lane's **sub-tasks** (rows like `3.2`). Parent rows (`3.`) are never worked on directly.
2. A sub-task is **ready** when it is unchecked and every task in its `Depends on:` line is checked `[x]`.
3. Required tasks come first. Optional tasks (`- [ ]*`) are done only when the person asks, or when no required task in your lane is ready.
4. If nothing is ready because you are waiting on the other lane, say exactly which task and handoff you are waiting for (H1 = 1.3, H2 = 3.6, H3 = 5.3) and stop.
5. If several tasks are ready and their `Files:` lists don't overlap, you may run them in parallel with sub-agents. Give each sub-agent its full task text, its `Files:` list, the relevant design sections, and an instruction to change nothing outside that list.
6. Never use the task runner's "run all tasks", because it would also run the other lane's tasks.

## 5. Implement a task

1. Read the acceptance criteria listed in the task's `_Requirements:_` line and the design sections it relies on.
2. Change only the paths in the task's `Files:` list, plus your own checkboxes in `tasks.md`. If you need to touch anything else, stop and explain why.
3. Write the task's tests along with the code, including the property tests the task names.
4. Meet the task's `Done when:` condition. A command exiting with 0 is not enough: check the actual output.
5. At a `[human]` step, prepare everything, show the person exactly what to decide or review, and stop. Don't check the task until the person confirms.

## 6. Finish a task

1. Run `scripts/check-all.sh`, or your lane's commands if the script does not exist yet.
2. Check the sub-task in `tasks.md`. If all required sub-tasks of its parent are now checked, check the parent too. Never edit the other lane's boxes.
3. Commit only your own files, with the message `lane-a(<task>): <summary>` or `lane-b(<task>): <summary>`. Contract changes use `contract: <summary>` and follow design section 4.5.
4. Run `git pull --rebase origin main`. If it brought in changes, re-run the checks. If a rebase conflict appears in a file you don't own, run `git rebase --abort` and ask the user.
5. Run `git push origin main`. Never force push, and never skip hooks.
6. When you finish a handoff task (1.3, 3.6, or 5.3), end the commit message with `H1 ready`, `H2 ready`, or `H3 ready`.

## 7. Continue or stop

Return to step 4 until no task is ready, a `[human]` step is reached, a check fails in a way you cannot fix inside your lane, or the user stops you. Then give a short report: tasks completed, commits pushed, what's next, and what is waiting on a person or on the other lane.

## Ownership

| Lane | Owns |
|---|---|
| A | `pipeline/`, `data/`, `contracts/` up to 1.0.0, tasks 1–5 |
| B | `web/`, tasks 6–10 |
| Shared | `scripts/check-all.sh`, `README.md`, own checkboxes in `tasks.md`, `contracts/` changes after 1.0.0 |

## Hard rules

- Never commit `data/raw/`, `captures/`, `.kiro/settings/`, secrets, or non-distributable source documents.
- Never trace, sample, or copy Google Maps, Google Earth, or Street View imagery or geometry.
- Never invent heights or label an estimate as official.
- Never force push, rewrite pushed history, or delete the other lane's work.
