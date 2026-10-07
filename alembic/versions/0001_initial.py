from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_crs", sa.String(255)),
        sa.Column("status", sa.Enum("PROCESSING", "COMPLETED", "FAILED", name="filestatus"), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_index", sa.Integer(), nullable=False),
        sa.Column("geometry_type", sa.String(50)),
        sa.Column("geometry", sa.JSON()),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("area", sa.Float()),
        sa.Column("area_unit", sa.String(20)),
        sa.Column("length", sa.Float()),
        sa.Column("length_unit", sa.String(20)),
        sa.Column("measurement_status", sa.String(30), nullable=False),
        sa.Column("measurement_message", sa.Text()),
    )
    op.create_index("ix_features_file_id", "features", ["file_id"])


def downgrade() -> None:
    op.drop_index("ix_features_file_id", table_name="features")
    op.drop_table("features")
    op.drop_table("files")
    sa.Enum(name="filestatus").drop(op.get_bind(), checkfirst=True)
