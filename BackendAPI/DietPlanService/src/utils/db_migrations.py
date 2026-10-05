# DietPlanService/src/utils/db_migrations.py
"""Start-up upgrades for databases created before a column or constraint existed.

Base.metadata.create_all only creates missing tables, never new columns or
constraints on an existing one (the service has no Alembic), so these small,
idempotent helpers bring an older database up to date. A fresh database already
has everything from create_all and these do nothing.
"""
import logging

from sqlalchemy import inspect, text

logger = logging.getLogger("diet_agent")

# column name -> SQL type, for diet_workflows columns added after the first release.
_WORKFLOW_COLUMNS = {
    "route": "VARCHAR(20)",
    "approver_role": "VARCHAR(20)",
    "decided_at": "TIMESTAMP WITH TIME ZONE",
}


def ensure_workflow_columns(engine) -> None:
    inspector = inspect(engine)
    if "diet_workflows" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("diet_workflows")}
    with engine.begin() as conn:
        for column, col_type in _WORKFLOW_COLUMNS.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE diet_workflows ADD COLUMN {column} {col_type}"))
                logger.info("migration: added diet_workflows.%s", column)


def ensure_plan_columns(engine) -> None:
    """Adds diet_plans.approval_status to databases created before pending plans existed."""
    inspector = inspect(engine)
    if "diet_plans" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("diet_plans")}
    if "approval_status" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE diet_plans ADD COLUMN approval_status VARCHAR(20) NOT NULL DEFAULT 'approved'"))
        logger.info("migration: added diet_plans.approval_status")


# constraint name -> condition. Added as NOT VALID: enforced for every new and changed row
# without failing start-up if an old row somehow holds another value.
_WORKFLOW_CHECKS = {
    "ck_diet_workflows_status": "status IN ('running','completed','failed','rejected')",
    "ck_diet_workflows_approval_status":
        "approval_status IS NULL OR approval_status IN ('pending','auto_approved','approved','rejected')",
    "ck_diet_workflows_risk_level": "risk_level IS NULL OR risk_level IN ('low','medium','high')",
}


def ensure_workflow_constraints(engine) -> None:
    """PostgreSQL only (SQLite cannot add a constraint to an existing table; a fresh
    database of either kind already has them from create_all)."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        existing = {
            row[0] for row in conn.execute(text(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'diet_workflows'::regclass"
            ))
        }
        for name, condition in _WORKFLOW_CHECKS.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE diet_workflows ADD CONSTRAINT {name} CHECK ({condition}) NOT VALID"))
                logger.info("migration: added constraint %s", name)
