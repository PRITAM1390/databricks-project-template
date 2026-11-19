# Databricks Project Template

Reusable Databricks bundle + CI/CD template. The same code deploys **dev → UAT → prod**; only configuration differs per environment.

- **Deployment:** Declarative Automation Bundles (`databricks.yml`)
- **CI/CD:** GitHub Actions (`.github/workflows/`)
- **Branches:** `dev` → dev, `uat` → UAT, `main` → prod

---

## 1. Repo layout

```
databricks.yml              # bundle config: targets (dev/uat/prod) and variables
resources/                  # what to deploy: schemas, jobs (YAML)
src/
  common/                   # shared Python modules (e.g. audit.py)
  pipelines/<layer>/        # pipeline code per layer (.py / .sql, incl. DML)
  ddl/<layer>/              # table definitions (CREATE / ALTER), run by CI
scripts/run_ddl.py          # CI tooling: runs DDL files through a SQL warehouse
tests/                      # unit tests
.github/workflows/
  ci-cd.yml                 # checks on PRs; checks + deploy on merge
  ddl-manual.yml            # manual "Run DDL" button
.github/CODEOWNERS          # who reviews which area
pyproject.toml              # ruff (lint) settings
requirements-dev.txt        # CI / developer tools (not used in Databricks)
```

`src/pipelines/` means pipeline code, not Lakeflow Declarative Pipelines.

---

## 2. New project setup

Do these once per project, in this order.

### 2.1 Databricks (platform admin)

Per environment (dev, UAT, prod):

1. **Workspace** for the environment.
2. **Catalogs** the project uses (e.g. `bronze_dev`, `silver_dev`, `gold_dev`). The bundle never creates catalogs.
   - With one Databricks account (shared metastore), **each environment must use its own catalog names**.
3. **Data access grants at catalog level** (e.g. analysts: `USE CATALOG`, `USE SCHEMA`, `SELECT` on gold catalogs). Done by Terraform or an admin, not by the bundle.
4. **Deploy service principal** (e.g. `github-deployer`):
   - Workspace access entitlement.
   - On each catalog: `USE CATALOG`, `CREATE SCHEMA`.
   - **Can use** on the SQL warehouse used for DDL.
   - Generate an OAuth secret (client ID + secret).
5. **Read-only CI service principal** for PR validation: workspace access only, no catalog grants, cannot deploy. Must exist in every workspace it validates.
6. **SQL warehouse** for DDL; note its ID (last part of the warehouse's HTTP path).
7. **Groups** used for job permissions (e.g. `data_engineer`, `data_analyst`).

> **Separate Databricks accounts per environment?** Identities must be created in each account, and the single `ci` environment below must become one per environment (`ci-dev`, `ci-uat`, `ci-prod`) with the checks job choosing by target.

### 2.2 GitHub (repo admin)

**Branches**
1. Create branches `dev` and `uat` from `main`:
   ```
   git checkout main            # start from main
   git branch dev               # create dev from main
   git branch uat               # create uat from main
   git push -u origin dev       # publish dev and track it
   git push -u origin uat       # publish uat and track it
   ```
2. **Settings → General → Default branch:** `dev`.
3. **Settings → General:** tick **Automatically delete head branches**.

**Environments** — Settings → Environments → New environment:

| Environment | Deployment branches | Secrets |
|---|---|---|
| `dev` | `dev` | `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` (deploy SP) |
| `uat` | `uat` | same names, UAT deploy SP |
| `prod` | `main` | same names, prod deploy SP |
| `ci` | No restriction | same names, **read-only CI SP** |

No required reviewers on environments — the PR approval is the gate.

**Branch protection** — Settings → Branches → add a rule for each of `dev`, `uat`, `main`:
- Require a pull request before merging
  - Require approvals: **1** (`uat`, `main`; optional on `dev`)
  - Dismiss stale pull request approvals when new commits are pushed
  - Require review from Code Owners (`uat`, `main`)
- Require status checks to pass: **`Validate bundle`**
  - Require branches to be up to date before merging
- Do not allow bypassing the above settings

`Validate bundle` only appears in the search after the workflow has run once on a PR.

**Security** — Settings → Code security:
- Enable **Secret Protection** and **Push protection**.
- Organization-owned repos: the gitleaks action needs a free license key stored as secret `GITLEAKS_LICENSE`.

### 2.3 Fill in the project values

- **`databricks.yml`:** replace every `REPLACE`: project name, workspace hosts, `root_path` (deploy SP ID), `run_as` service principal, catalogs, `sql_warehouse_id`, `alerts`, `groups`.
- **`.github/CODEOWNERS`:** replace owners with your users/teams.
- Delete the sample job and sample DDL once you have real ones.

---

## 3. Branching and promotion

```
feature/* ──PR──► dev ──PR──► uat ──PR──► main
                  (dev env)   (UAT env)   (prod env)
```

| Branch type | Created from | PR into | Merge method |
|---|---|---|---|
| `feature/<ticket>-<desc>` | `dev` | `dev` | **Squash** |
| `bugfix/<ticket>-<desc>` | `dev` | `dev` | **Squash** |
| Promotion | — | `dev` → `uat`, `uat` → `main` | **Create a merge commit** |
| `hotfix/<ticket>-<desc>` | `main` | `main` | Squash |
| Back-merge | — | `main` → `uat`, `main` → `dev` | **Create a merge commit** |

**Rules**
- Merging into `dev` means "ready for UAT". Keep unfinished work on its feature branch.
- `uat` and `main` only receive promotion, hotfix and back-merge PRs. No direct commits.
- Never squash promotions or back-merges — squashing disconnects branch histories and causes repeated diffs and conflicts.
- Never reuse a branch after it has been squash-merged; start a new one from `dev`.

### 3.1 Feature

```
git checkout dev                         # start from dev
git pull                                 # get the latest dev
git checkout -b feature/EDP-12-sap       # new feature branch
# ...work, test in personal dev (section 4)...
git add .                                # stage changes
git commit -m "EDP-12 SAP ingestion"     # save locally
git push -u origin feature/EDP-12-sap    # publish the branch
```
Open a PR into `dev`, wait for checks, squash and merge.

### 3.2 Promotion

On GitHub: **New pull request → base `uat`, compare `dev`** (or base `main`, compare `uat`). Review **Files changed**, wait for checks, approve, **Create a merge commit**.

### 3.3 Manual partial release (exception only)

To promote only some changes to UAT, cherry-pick their commits (one commit per squashed feature PR):
```
git checkout uat                         # start from uat
git pull                                 # get the latest uat
git checkout -b promote/uat-EDP-12       # temporary promotion branch
git cherry-pick <commit-id>              # copy the feature's commit from dev
git push -u origin promote/uat-EDP-12    # publish
```
Open a PR into `uat`. Include any commits the feature depends on (e.g. shared config). Resolve conflicts, then `git cherry-pick --continue` (or `--abort`).

### 3.4 Hotfix

```
git checkout main                        # start from prod code
git pull                                 # get the latest main
git checkout -b hotfix/EDP-99-fix        # hotfix branch
# ...fix, commit, push...
```
1. PR into `main` → checks → merge → prod deploys.
2. **Verify the fix in prod.**
3. **Back-merge immediately:** PR `main` → `uat` and PR `main` → `dev`, merge commit. If the hotfix failed, don't back-merge — revert or fix on `main` first.

### 3.5 Why environment branches (not trunk-based)

Databricks recommends trunk-based development. This template uses environment branches so that every promotion is an explicit, reviewable PR, approvals work on GitHub Team plans (environment approvals in private repos need GitHub Enterprise), and the prod branch always shows exactly what is in prod.

---

## 4. Developer workflow (personal dev)

Test your feature branch in your own copy of dev before opening a PR. Dev mode prefixes your jobs and schemas with your username, so you don't affect anyone else.

One-time setup:
```
pip install -r requirements-dev.txt                              # ruff + Databricks SDK
databricks auth login --host <dev-workspace-url> --profile dev   # log in once
```

Each time:
```
ruff check .                                                     # lint
databricks bundle validate -t dev                                # check config
databricks bundle deploy -t dev                                  # deploy your copy
python scripts/run_ddl.py -t dev src/ddl/bronze/<file>.sql       # create your tables
databricks bundle run <job_name> -t dev                          # run a job
```
After your PR is merged:
```
databricks bundle destroy -t dev --auto-approve                  # remove your copy
```

---

## 5. CI/CD: what runs when

| Event | What runs |
|---|---|
| PR into `dev` / `uat` / `main` | **Checks:** ruff lint, gitleaks secret scan, `bundle validate` against the target branch's environment |
| Merge into `dev` / `uat` / `main` | **Checks** again, then **Deploy** to that environment |
| Merge with only `.md` changes | Nothing deployed |

**Deploy job:**
1. `databricks bundle deploy -t <target>` — applies only differences (files, jobs, schemas, permissions). In UAT/prod, `prevent_destroy` blocks deletion of schemas.
2. **Run changed DDL** — runs only `.sql` files added or modified under `src/ddl/` in that merge, through the target's SQL warehouse, as the service principal.

Deploy does **not** run data jobs; they run on their schedules (paused in dev) or when triggered.

---

## 6. DDL rules

- **Location:** `src/ddl/<bronze|silver|gold>/`. Files elsewhere fail.
- **One SQL statement per file.**
- **Never hardcode catalogs or schemas.** Use the parameters:
  ```sql
  CREATE TABLE IF NOT EXISTS IDENTIFIER(:catalog || '.' || :schema || '.orders') (...)
  ```
- **Never edit a DDL file after it has run.** Editing a `CREATE ... IF NOT EXISTS` does not change an existing table, and re-running an `ALTER` fails. Put every change in a **new file**.
- **Naming (for run order):** `<table>.sql` for the create, `<table>_001_<change>.sql`, `<table>_002_<change>.sql` for changes. Files run bronze → silver → gold, then alphabetically.
- **No `CREATE OR REPLACE`** on tables holding data.

**If a DDL run fails:**
- Temporary issue (e.g. warehouse stopped): Actions → the failed run → **Re-run failed jobs**.
- After a fix merged in a later PR: Actions → **Run DDL manually** → choose the branch, the matching environment and the file(s). The environment only accepts its own branch.

---

## 7. Configuration reference (`databricks.yml`)

| Variable | Purpose | Used as |
|---|---|---|
| `catalogs` | Catalog per layer (map) | `${var.catalogs.bronze}` |
| `alerts` | Failure-alert email per team (map, group mailboxes) | `${var.alerts.platform}` |
| `groups` | Workspace groups for job permissions (map) | `${var.groups.engineers}` |
| `sql_warehouse_id` | Warehouse used by CI to run DDL | read by `scripts/run_ddl.py` |

- **One catalog for everything:** set every layer to the same catalog name.
- **More catalogs, teams or groups:** add a key in **every** target, then reference `${var.<map>.<key>}`.
- **Job permissions** are set per target: dev `CAN_MANAGE`, UAT `CAN_RUN`, prod `CAN_VIEW` for engineers; analysts `CAN_VIEW`.
- **Failure emails:** add `email_notifications.on_failure` to each job with the owning team + `platform`.

---

## 8. Permissions and secrets

- Job permissions on bundle-deployed jobs are managed **only in `databricks.yml`**. Changes made in the UI are overwritten on the next deploy.
- Group membership (who is in `data_engineer`) is managed by the identity admin, not in code.
- **Never commit secrets.**
  - CI/CD credentials: GitHub environment secrets.
  - Source system passwords / API keys: Databricks secret scopes per environment, read in code with `dbutils.secrets.get(scope, key)`.

---

## 9. Rollback

| What broke | How to roll back |
|---|---|
| Jobs, code, permissions | **Revert** the PR on GitHub and merge the revert; CI redeploys the previous state. Prod: revert on `main` (hotfix path) and back-merge, or revert in `dev` and promote. |
| Table structure | Forward-only: add a **new** DDL file that undoes the change. Reverting a PR does not undo DDL. |
| Data | Delta time travel: restore the table to its version before the bad run. |

> **Revert the revert:** after reverting a promotion merge on `main`, the next `uat → main` promotion will **not** bring those commits back. To re-release them, revert the revert commit.

**Emergency:** re-running an older successful deploy run redeploys that commit, but the next merge redeploys the branch — always follow with a proper revert.

---

## 10. Maintenance

**Upgrade the Databricks CLI** (pinned for consistency):
1. Change `version:` in every "Install Databricks CLI" step in `.github/workflows/` (via PR).
2. Everyone updates their local CLI to the same version and checks with `databricks -v`.

**Tool versions** in `requirements-dev.txt` are pinned; upgrade them via PR.

**Expected warnings (safe to ignore):**
- `workspace folder has permissions not configured in bundle` — the deployer always has CAN_MANAGE on its own folder.
