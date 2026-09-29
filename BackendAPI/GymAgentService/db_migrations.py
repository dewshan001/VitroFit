"""Small idempotent schema upgrades for databases created before a model change.

`Base.metadata.create_all` builds new tables in full but never alters existing ones, so
changes to an existing table are applied here. Everything is safe to run on every start.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("gym_agent")

DETAILS_TABLE = "gym_agent_details"
WORKFLOWS_TABLE = "gym_agent_workflows"
FK_NAME = "fk_gym_details_verified_workflow"
CHECK_NAME = "ck_gym_details_verified_has_workflow"


def _constraint_exists(conn, table: str, name: str) -> bool:
    return (
        conn.execute(
            text("SELECT 1 FROM pg_constraint WHERE conname = :n AND conrelid = CAST(:t AS regclass)"),
            {"n": name, "t": table},
        ).first()
        is not None
    )


def ensure_gym_details_provenance(engine: Engine) -> None:
    """Make 'verified' rows traceable to an approved workflow, and let the database refuse
    any other way of becoming verified.

    Adds verified_workflow_id / verified_by / verified_at, backfills rows that were published
    by an earlier version from their latest Published workflow, and adds the CHECK constraint
    as NOT VALID: it is enforced for every new or changed row, but does not fail the upgrade
    if a legacy verified row has no workflow behind it (for example one set by hand).

    PostgreSQL only. On other databases (tests use SQLite) tables are created by create_all
    with the constraint already defined, so there is nothing to upgrade.
    """
    if engine.dialect.name != "postgresql":
        return
    tables = set(inspect(engine).get_table_names())
    if DETAILS_TABLE not in tables or WORKFLOWS_TABLE not in tables:
        return

    with engine.begin() as conn:
        conn.execute(text(
            f"ALTER TABLE {DETAILS_TABLE} "
            "ADD COLUMN IF NOT EXISTS verified_workflow_id VARCHAR(36), "
            "ADD COLUMN IF NOT EXISTS verified_by VARCHAR(100), "
            "ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ"
        ))

        if not _constraint_exists(conn, DETAILS_TABLE, FK_NAME):
            conn.execute(text(
                f"ALTER TABLE {DETAILS_TABLE} ADD CONSTRAINT {FK_NAME} "
                f"FOREIGN KEY (verified_workflow_id) REFERENCES {WORKFLOWS_TABLE}(id) ON DELETE RESTRICT"
            ))

        backfilled = conn.execute(text(
            f"""
            UPDATE {DETAILS_TABLE} d
               SET verified_workflow_id = w.id,
                   verified_by = w.approved_by,
                   verified_at = COALESCE(w.decided_at, d.updated_at)
              FROM (
                    SELECT DISTINCT ON (place_id) id, place_id, approved_by, decided_at
                      FROM {WORKFLOWS_TABLE}
                     WHERE status = 'Published' AND approved_by IS NOT NULL
                     ORDER BY place_id, COALESCE(decided_at, updated_at) DESC
                   ) w
             WHERE d.place_id = w.place_id
               AND d.source = 'verified'
               AND d.verified_workflow_id IS NULL
            """
        )).rowcount
        if backfilled:
            logger.info("Linked %d existing verified gym(s) to their approving workflow", backfilled)

        if not _constraint_exists(conn, DETAILS_TABLE, CHECK_NAME):
            conn.execute(text(
                f"ALTER TABLE {DETAILS_TABLE} ADD CONSTRAINT {CHECK_NAME} "
                "CHECK (source <> 'verified' OR verified_workflow_id IS NOT NULL) NOT VALID"
            ))

        orphans = conn.execute(text(
            f"SELECT count(*) FROM {DETAILS_TABLE} WHERE source = 'verified' AND verified_workflow_id IS NULL"
        )).scalar()
        if orphans:
            logger.warning(
                "%d verified gym(s) have no approving workflow (set outside the approval flow). "
                "They are left as they are; re-verify them through a workflow.", orphans
            )


def ensure_tool_call_guard_flags(engine: Engine) -> None:
    """Add gym_agent_tool_calls.guard_flags (prompt-injection findings) to a database created before it.

    Additive and idempotent. PostgreSQL only; other databases get the column from create_all.
    """
    if engine.dialect.name != "postgresql":
        return
    if "gym_agent_tool_calls" not in set(inspect(engine).get_table_names()):
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE gym_agent_tool_calls ADD COLUMN IF NOT EXISTS guard_flags VARCHAR(200)"))
