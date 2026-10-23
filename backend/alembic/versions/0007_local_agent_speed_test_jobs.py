"""Queue speed tests for the Local Agent."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_local_agent_speed_tests"
down_revision: Union[str, Sequence[str], None] = "0006_one_time_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speed_test_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ip", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("download_mbps", sa.Float(), nullable=True),
        sa.Column("upload_mbps", sa.Float(), nullable=True),
        sa.Column("ping_ms", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_speed_test_jobs_id", "speed_test_jobs", ["id"])
    op.create_index("ix_speed_test_jobs_status", "speed_test_jobs", ["status"])
    op.create_index(
        "ix_speed_test_jobs_status_created",
        "speed_test_jobs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_speed_test_jobs_status_created", table_name="speed_test_jobs")
    op.drop_index("ix_speed_test_jobs_status", table_name="speed_test_jobs")
    op.drop_index("ix_speed_test_jobs_id", table_name="speed_test_jobs")
    op.drop_table("speed_test_jobs")
