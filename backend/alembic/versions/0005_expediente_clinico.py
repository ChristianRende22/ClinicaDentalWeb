"""expediente clinico: tratamiento, consulta, diagnostico, odontograma,
pieza_dental, plan_tratamiento, plan_tratamiento_detalle, presupuesto,
receta, receta_detalle, y Cita.id_tratamiento

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-05

Nota sobre el defecto #1 del Modulo 4 (indice en la migracion y no en el
modelo): esta migracion no agrega ningun indice nuevo aparte de los que ya
imponen las UniqueConstraint, asi que no hay riesgo de esa divergencia
puntual. Si se agrega un indice de consulta (ej. para el historial por
paciente) hay que declararlo tambien en el modelo, no solo aca.
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_ESTADOS_PIEZA = ("sano", "cariado", "obturado", "ausente", "corona", "endodoncia", "implante")
_ESTADOS_PLAN = ("borrador", "aprobado", "en_progreso", "completado", "cancelado")
_ESTADOS_DETALLE = ("pendiente", "en_progreso", "completado", "cancelado")
_ESTADOS_PRESUPUESTO = ("vigente", "aceptado", "rechazado", "vencido")


def upgrade() -> None:
    op.create_table(
        "tratamiento",
        sa.Column("id_tratamiento", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("precio", sa.Numeric(10, 2), nullable=False),
        sa.Column("duracion_minutos_estimada", sa.Integer(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.PrimaryKeyConstraint("id_tratamiento"),
        sa.UniqueConstraint("id_clinica", "nombre", name="uq_tratamiento_clinica_nombre"),
    )

    op.create_table(
        "consulta",
        sa.Column("id_consulta", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=False),
        sa.Column("id_cita", sa.Integer(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.ForeignKeyConstraint(["id_cita"], ["cita.id_cita"]),
        sa.PrimaryKeyConstraint("id_consulta"),
    )

    op.create_table(
        "diagnostico",
        sa.Column("id_diagnostico", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_consulta", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("pieza_numero", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_consulta"], ["consulta.id_consulta"]),
        sa.PrimaryKeyConstraint("id_diagnostico"),
    )

    op.create_table(
        "odontograma",
        sa.Column("id_odontograma", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.PrimaryKeyConstraint("id_odontograma"),
        sa.UniqueConstraint("id_paciente", name="uq_odontograma_paciente"),
    )

    op.create_table(
        "pieza_dental",
        sa.Column("id_pieza", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_odontograma", sa.Integer(), nullable=False),
        sa.Column("numero_pieza", sa.Integer(), nullable=False),
        sa.Column("estado", sa.Enum(*_ESTADOS_PIEZA, name="estado_pieza_dental"), server_default="sano", nullable=False),
        sa.Column("observaciones", sa.String(length=255), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_odontograma"], ["odontograma.id_odontograma"]),
        sa.PrimaryKeyConstraint("id_pieza"),
        sa.UniqueConstraint(
            "id_odontograma", "numero_pieza", name="uq_pieza_odontograma_numero"
        ),
    )

    op.create_table(
        "plan_tratamiento",
        sa.Column("id_plan", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(*_ESTADOS_PLAN, name="estado_plan_tratamiento"),
            server_default="borrador",
            nullable=False,
        ),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.PrimaryKeyConstraint("id_plan"),
    )

    op.create_table(
        "plan_tratamiento_detalle",
        sa.Column("id_detalle", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_plan", sa.Integer(), nullable=False),
        sa.Column("id_tratamiento", sa.Integer(), nullable=False),
        sa.Column("pieza_numero", sa.Integer(), nullable=True),
        sa.Column("cantidad", sa.Integer(), server_default="1", nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(*_ESTADOS_DETALLE, name="estado_detalle_plan_tratamiento"),
            server_default="pendiente",
            nullable=False,
        ),
        sa.Column("orden", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_plan"], ["plan_tratamiento.id_plan"]),
        sa.ForeignKeyConstraint(["id_tratamiento"], ["tratamiento.id_tratamiento"]),
        sa.PrimaryKeyConstraint("id_detalle"),
    )

    op.create_table(
        "presupuesto",
        sa.Column("id_presupuesto", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_plan", sa.Integer(), nullable=False),
        sa.Column("monto_total", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(*_ESTADOS_PRESUPUESTO, name="estado_presupuesto"),
            server_default="vigente",
            nullable=False,
        ),
        sa.Column(
            "fecha_emision", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_plan"], ["plan_tratamiento.id_plan"]),
        sa.PrimaryKeyConstraint("id_presupuesto"),
        sa.UniqueConstraint("id_plan", name="uq_presupuesto_plan"),
    )

    op.create_table(
        "receta",
        sa.Column("id_receta", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=False),
        sa.Column("id_consulta", sa.Integer(), nullable=True),
        sa.Column(
            "fecha_emision", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("indicaciones_generales", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.ForeignKeyConstraint(["id_consulta"], ["consulta.id_consulta"]),
        sa.PrimaryKeyConstraint("id_receta"),
    )

    op.create_table(
        "receta_detalle",
        sa.Column("id_detalle", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_receta", sa.Integer(), nullable=False),
        sa.Column("medicamento", sa.String(length=100), nullable=False),
        sa.Column("dosis", sa.String(length=50), nullable=False),
        sa.Column("frecuencia", sa.String(length=50), nullable=False),
        sa.Column("duracion", sa.String(length=50), nullable=True),
        sa.Column("indicaciones", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_receta"], ["receta.id_receta"]),
        sa.PrimaryKeyConstraint("id_detalle"),
    )

    op.add_column(
        "cita",
        sa.Column("id_tratamiento", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_cita_tratamiento", "cita", "tratamiento", ["id_tratamiento"], ["id_tratamiento"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_cita_tratamiento", "cita", type_="foreignkey")
    op.drop_column("cita", "id_tratamiento")
    op.drop_table("receta_detalle")
    op.drop_table("receta")
    op.drop_table("presupuesto")
    op.drop_table("plan_tratamiento_detalle")
    op.drop_table("plan_tratamiento")
    op.drop_table("pieza_dental")
    op.drop_table("odontograma")
    op.drop_table("diagnostico")
    op.drop_table("consulta")
    op.drop_table("tratamiento")
