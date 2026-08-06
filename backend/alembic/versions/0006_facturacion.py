"""facturacion: factura, factura_detalle, pago

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_ESTADOS_FACTURA = ("pendiente", "parcial", "pagada", "anulada")


def upgrade() -> None:
    op.create_table(
        "factura",
        sa.Column("id_factura", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clinica", sa.Integer(), nullable=False),
        sa.Column("id_paciente", sa.Integer(), nullable=False),
        sa.Column("id_doctor", sa.Integer(), nullable=True),
        sa.Column("id_asistente", sa.Integer(), nullable=True),
        sa.Column("id_plan", sa.Integer(), nullable=True),
        sa.Column("numero_factura", sa.String(length=20), nullable=False),
        sa.Column("monto_subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("monto_impuesto", sa.Numeric(10, 2), nullable=False),
        sa.Column("monto_total", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(*_ESTADOS_FACTURA, name="estado_factura"),
            server_default="pendiente",
            nullable=False,
        ),
        sa.Column(
            "fecha_emision", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_clinica"], ["clinica.id_clinica"]),
        sa.ForeignKeyConstraint(["id_paciente"], ["paciente.id_paciente"]),
        sa.ForeignKeyConstraint(["id_doctor"], ["doctor.id_doctor"]),
        sa.ForeignKeyConstraint(["id_asistente"], ["asistente.id_asistente"]),
        sa.ForeignKeyConstraint(["id_plan"], ["plan_tratamiento.id_plan"]),
        sa.PrimaryKeyConstraint("id_factura"),
        sa.UniqueConstraint("id_clinica", "numero_factura", name="uq_factura_clinica_numero"),
        sa.UniqueConstraint("id_plan", name="uq_factura_plan"),
    )

    op.create_table(
        "factura_detalle",
        sa.Column("id_detalle", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_factura", sa.Integer(), nullable=False),
        sa.Column("id_tratamiento", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), server_default="1", nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["id_factura"], ["factura.id_factura"]),
        sa.ForeignKeyConstraint(["id_tratamiento"], ["tratamiento.id_tratamiento"]),
        sa.PrimaryKeyConstraint("id_detalle"),
    )

    op.create_table(
        "pago",
        sa.Column("id_pago", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_factura", sa.Integer(), nullable=False),
        sa.Column("id_metodo_pago", sa.Integer(), nullable=False),
        sa.Column("id_asistente", sa.Integer(), nullable=True),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "fecha_pago", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["id_factura"], ["factura.id_factura"]),
        sa.ForeignKeyConstraint(["id_metodo_pago"], ["metodo_pago.id_metodo_pago"]),
        sa.ForeignKeyConstraint(["id_asistente"], ["asistente.id_asistente"]),
        sa.PrimaryKeyConstraint("id_pago"),
    )


def downgrade() -> None:
    op.drop_table("pago")
    op.drop_table("factura_detalle")
    op.drop_table("factura")
