"""parametros por clinica: especialidad, consultorio, metodo_pago, horario, configuracion

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _tabla_catalogo(nombre_tabla: str, nombre_pk: str) -> None:
    op.create_table(
        nombre_tabla,
        sa.Column(nombre_pk, sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint(nombre_pk),
        sa.UniqueConstraint(
            "id_clinica", "nombre", name=f"uq_{nombre_tabla}_clinica_nombre"
        ),
    )


def upgrade() -> None:
    _tabla_catalogo("especialidad", "id_especialidad")
    _tabla_catalogo("consultorio", "id_consultorio")
    _tabla_catalogo("metodo_pago", "id_metodo_pago")

    op.create_table(
        "horario_clinica",
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column(
            "dia_semana",
            sa.Enum(
                "lunes",
                "martes",
                "miercoles",
                "jueves",
                "viernes",
                "sabado",
                "domingo",
                name="dia_semana",
            ),
            nullable=False,
        ),
        sa.Column("hora_apertura", sa.Time(), nullable=True),
        sa.Column("hora_cierre", sa.Time(), nullable=True),
        sa.Column("cerrado", sa.Boolean(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint("id_clinica", "dia_semana"),
    )

    op.create_table(
        "configuracion_clinica",
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column(
            "duracion_cita_minutos", sa.Integer(), server_default="30", nullable=False
        ),
        sa.Column(
            "porcentaje_impuesto",
            sa.Numeric(precision=5, scale=2),
            server_default="13.00",
            nullable=False,
        ),
        sa.Column(
            "prefijo_factura", sa.String(length=10), server_default="F", nullable=False
        ),
        sa.Column(
            "proximo_numero_factura", sa.Integer(), server_default="1", nullable=False
        ),
        sa.Column(
            "horas_minimas_cambio_cita", sa.Integer(), server_default="24", nullable=False
        ),
        sa.Column(
            "dias_minimos_reagendamiento", sa.Integer(), server_default="3", nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint("id_clinica"),
    )


def downgrade() -> None:
    op.drop_table("configuracion_clinica")
    op.drop_table("horario_clinica")
    op.drop_table("metodo_pago")
    op.drop_table("consultorio")
    op.drop_table("especialidad")
