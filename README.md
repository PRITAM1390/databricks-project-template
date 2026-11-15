# Databricks Project Template

Reusable bundle + CI/CD template. The same code deploys dev → UAT → prod; only config changes.

## New project setup
1. Copy this repo.
2. In `databricks.yml`, replace every `REPLACE` value (project name, workspace URLs, catalogs, service principals).
3. Make sure the catalogs exist in each workspace (created by Terraform/admin, not by this bundle).
4. Deploy and set up tables:
       databricks bundle deploy -t dev
       databricks bundle run ddl_setup -t dev

## Folder layout
- `resources/`: what to deploy (schemas, jobs)
- `src/pipelines/<layer>/`: logic that moves data (.py and .sql, including DML)
- `src/ddl/<layer>/`: table definitions only (CREATE/ALTER), must be re-runnable (IF NOT EXISTS)
- `src/common/`: shared Python modules
- `config/`: project settings
- `tests/`: unit tests
- `.github/workflows/`: CI/CD pipeline

Note: `src/pipelines/` means pipeline code, not Lakeflow Declarative Pipelines.

## Catalogs
- One catalog: set `bronze`, `silver`, `gold` to the same name.
- Multiple catalogs: set different names; add keys if needed and use `${var.catalogs.<key>}`.
- Never hardcode catalog or schema names in code; always pass them as job parameters.

## DDL
- One SQL file per table in `src/ddl/<layer>/`, added as a task in `resources/ddl_job.yml`.
- `bundle deploy` does not execute code. Run `ddl_setup` after every deploy (CI/CD will automate this).

## Shared code
Put reusable Python in `src/common/` (plain .py files, not notebooks). Import in notebooks with:

    import os, sys
    sys.path.append(os.path.abspath("../.."))   # from src/pipelines/<layer>/
    from common.audit import add_audit_columns

Don't name modules after Python standard libraries (e.g. logging.py).

## Secrets
Never commit secrets. CI/CD credentials go in GitHub Environment secrets; source passwords and API keys go in Databricks secret scopes (set once per environment). Code reads them with `dbutils.secrets.get(scope, key)`.

## Environments
- dev: personal copies (names prefixed per developer), schedules paused
- uat / prod: deployed by CI/CD after approval, run as a service principal