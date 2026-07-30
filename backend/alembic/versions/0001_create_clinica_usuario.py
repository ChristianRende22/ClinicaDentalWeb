"""create clinica, clinica_modulo y usuario

Revision ID: 0001
Revises:
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinica",
        sa.Column("id_clinica", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("direccion", sa.String(length=150), nullable=True),
        sa.Column("telefono", sa.String(length=8), nullable=True),
        sa.Column("correo", sa.String(length=100), nullable=True),
        sa.Column(
            "estado",
            sa.Enum("activa", "suspendida", "inactiva", name="estado_clinica"),
            nullable=False,
            server_default="activa",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "clinica_modulo",
        sa.Column(
            "id_clinica",
            sa.Integer(),
            sa.ForeignKey("clinica.id_clinica"),
            primary_key=True,
        ),
        sa.Column("modulo", sa.String(length=50), primary_key=True),
        sa.Column("habilitado", sa.Boolean(), nullable=False, server_default="1"),
    )

    op.create_table(
        "usuario",
        sa.Column("id_usuario", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "id_clinica", sa.Integer(), sa.ForeignKey("clinica.id_clinica"), nullable=True
        ),
        sa.Column("username", sa.String(length=30), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum("superadmin", "admin", "doctor", "asistente", name="rol_usuario"),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("usuario")
    op.drop_table("clinica_modulo")
    op.drop_table("clinica")
