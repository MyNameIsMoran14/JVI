"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "editor", "viewer", name="user_role", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("diagnosis_date", sa.Date(), nullable=True),
        sa.Column("stage", sa.String(length=50), nullable=True),
        sa.Column("paraprotein_type", sa.String(length=50), nullable=True),
        sa.Column("comorbidities", postgresql.JSONB(), nullable=False),
        sa.Column("allergies", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("lab", "discharge", "imaging", "other", name="document_kind", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("taken_at", sa.Date(), nullable=True),
        sa.Column("lab_name", sa.String(length=200), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded", "parsing", "needs_review", "confirmed", "failed",
                name="document_status", native_enum=False, length=20,
            ),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_documents_patient_id_patients"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name="fk_documents_uploaded_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("sha256", name="uq_documents_sha256"),
    )
    op.create_index("ix_documents_patient_id", "documents", ["patient_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])

    op.create_table(
        "analytes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name_ru", sa.String(length=200), nullable=False),
        sa.Column("canonical_unit", sa.String(length=30), nullable=True),
        sa.Column("aliases", postgresql.JSONB(), nullable=False),
        sa.Column("group", sa.String(length=100), nullable=False),
        sa.Column("is_key", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_analytes"),
        sa.UniqueConstraint("code", name="uq_analytes_code"),
    )
    op.create_index("ix_analytes_code", "analytes", ["code"])

    op.create_table(
        "unit_conversions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analyte_id", sa.Integer(), nullable=False),
        sa.Column("from_unit", sa.String(length=30), nullable=False),
        sa.Column("factor", sa.Numeric(18, 6), nullable=False),
        sa.ForeignKeyConstraint(["analyte_id"], ["analytes.id"], name="fk_unit_conversions_analyte_id_analytes"),
        sa.PrimaryKeyConstraint("id", name="pk_unit_conversions"),
        sa.UniqueConstraint("analyte_id", "from_unit", name="uq_unit_conversions_analyte_id_from_unit"),
    )
    op.create_index("ix_unit_conversions_analyte_id", "unit_conversions", ["analyte_id"])

    op.create_table(
        "lab_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("analyte_id", sa.Integer(), nullable=False),
        sa.Column("taken_at", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=True),
        sa.Column("value_text", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("value_canonical", sa.Numeric(18, 6), nullable=True),
        sa.Column("ref_low", sa.Numeric(18, 6), nullable=True),
        sa.Column("ref_high", sa.Numeric(18, 6), nullable=True),
        sa.Column(
            "flag", sa.Enum("L", "H", "N", name="result_flag", native_enum=False, length=10), nullable=True
        ),
        sa.Column("raw_name", sa.String(length=200), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_lab_results_document_id_documents"),
        sa.ForeignKeyConstraint(["analyte_id"], ["analytes.id"], name="fk_lab_results_analyte_id_analytes"),
        sa.PrimaryKeyConstraint("id", name="pk_lab_results"),
    )
    op.create_index("ix_lab_results_document_id", "lab_results", ["document_id"])
    op.create_index("ix_lab_results_analyte_id", "lab_results", ["analyte_id"])
    op.create_index("ix_lab_results_taken_at", "lab_results", ["taken_at"])

    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("doctor", sa.String(length=200), nullable=True),
        sa.Column("clinic", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("decisions", sa.Text(), nullable=True),
        sa.Column("next_visit_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_visits_patient_id_patients"),
        sa.PrimaryKeyConstraint("id", name="pk_visits"),
    )
    op.create_index("ix_visits_patient_id", "visits", ["patient_id"])
    op.create_index("ix_visits_date", "visits", ["date"])

    op.create_table(
        "treatments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("regimen", sa.String(length=200), nullable=False),
        sa.Column("cycle_no", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_treatments_patient_id_patients"),
        sa.PrimaryKeyConstraint("id", name="pk_treatments"),
    )
    op.create_index("ix_treatments_patient_id", "treatments", ["patient_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_conversations_patient_id_patients"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_conversations_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index("ix_conversations_patient_id", "conversations", ["patient_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="message_role", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], name="fk_messages_conversation_id_conversations"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "doctor_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "asked", "answered", name="question_status", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("visit_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_doctor_questions_patient_id_patients"),
        sa.ForeignKeyConstraint(
            ["source_message_id"], ["messages.id"], name="fk_doctor_questions_source_message_id_messages"
        ),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], name="fk_doctor_questions_visit_id_visits"),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_questions"),
    )
    op.create_index("ix_doctor_questions_patient_id", "doctor_questions", ["patient_id"])

    op.create_table(
        "patient_summary",
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_patient_summary_patient_id_patients"),
        sa.PrimaryKeyConstraint("patient_id", name="pk_patient_summary"),
    )


def downgrade() -> None:
    op.drop_table("patient_summary")
    op.drop_table("doctor_questions")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("treatments")
    op.drop_table("visits")
    op.drop_table("lab_results")
    op.drop_table("unit_conversions")
    op.drop_table("analytes")
    op.drop_table("documents")
    op.drop_table("patients")
    op.drop_table("users")
