from alembic import op
import sqlalchemy as sa

revision = "0002_measurement_crs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("features", sa.Column("measurement_crs", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("features", "measurement_crs")
