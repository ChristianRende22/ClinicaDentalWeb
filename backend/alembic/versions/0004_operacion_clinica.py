"""operacion clinica: paciente, doctor, asistente, horario_doctor, cita

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
_ESTADOS = ("programada", "confirmada", "completada", "cancelada", "no_asistio")


def _columnas_de_persona() -> list[sa.Column]:
    return [
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("apellido", sa.String(length=50), nullable=False),
        sa.Column("telefono", sa.String(length=15), nullable=False),
        sa.Column("correo", sa.String(length=100), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="1", nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "paciente",
        sa.Column("id_paciente", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("direccion", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        *_columnas_de_persona(),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint("id_paciente"),
    )

    op.create_table(
        "doctor",
        sa.Column("id_doctor", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_especialidad", sa.Integer(), nullable=True),
        *_columnas_de_persona(),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["id_especialidad"], ["especialidad.id_especialidad"]),
        sa.PrimaryKeyConstraint("id_doctor"),
        sa.UniqueConstraint("id_usuario", name="uq_doctor_usuario"),
    )

    op.create_table(
        "asistente",
        sa.Column("id_asistente", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        *_columnas_de_persona(),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_asistente"),
        sa.UniqueConstraint("id_usuario", name="uq_asistente_usuario"),
    )

    op.create_table(
        "horario_doctor",
        sa.Column("id_horario", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Enum(*_DIAS, name="dia_semana"), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.Column("disponible", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.PrimaryKeyConstraint("id_horario"),
        sa.UniqueConstraint(
            "id_doctor", "dia_semana", "hora_inicio", name="uq_horario_doctor_dia_inicio"
        ),
    )

    op.create_table(
        "cita",
        sa.Column("id_cita", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=False),
        sa.Column("id_consultorio", sa.Integer(), nullable=True),
        sa.Column("id_asistente", sa.Integer(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(), nullable=False),
        sa.Column("duracion_minutos", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(*_ESTADOS, name="estado_cita"),
            server_default="programada",
            nullable=False,
        ),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("veces_reagendada", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.ForeignKeyConstraint(["id_consultorio"], ["consultorio.id_consultorio"]),
        sa.ForeignKeyConstraint(["id_asistente"], ["asistente.id_asistente"]),
        sa.PrimaryKeyConstraint("id_cita"),
    )
    # Indice para el caso de uso central: la agenda de un doctor en un rango.
    op.create_index("ix_cita_doctor_fecha", "cita", ["id_doctor", "fecha_hora"])

    op.add_column(
        "configuracion_clinica",
        sa.Column(
            "anticipacion_minima_reserva_horas",
            sa.Integer(),
            server_default="24",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("configuracion_clinica", "anticipacion_minima_reserva_horas")
    op.drop_index("ix_cita_doctor_fecha", table_name="cita")
    op.drop_table("cita")
    op.drop_table("horario_doctor")
    op.drop_table("asistente")
    op.drop_table("doctor")
    op.drop_table("paciente")
