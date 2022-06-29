"""First migration

Revision ID: 4210397a484e
Revises:
Create Date: 2022-06-29 21:11:33.154310

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4210397a484e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "matches",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(length=23), nullable=False),
        sa.Column("uhash", sa.String(length=5), nullable=True),
        sa.Column("code", sa.String(length=4), nullable=True),
        sa.Column("password", sa.String(length=5), nullable=True),
        sa.Column("is_restricted", sa.Boolean(), nullable=True),
        sa.Column("from_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("to_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("times", sa.Integer(), nullable=True),
        sa.Column("order", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_matches")),
        sa.UniqueConstraint("name", name=op.f("uq_matches_name")),
    )
    op.create_table(
        "open_answers",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("text", sa.String(length=2000), nullable=False),
        sa.Column("content_url", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_open_answers")),
    )
    op.create_table(
        "users",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("email_digest", sa.String(length=32), nullable=True),
        sa.Column("token_digest", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=30), nullable=True),
        sa.Column("password_hash", sa.String(length=60), nullable=True),
        sa.Column("key", sa.String(length=32), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "games",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_uid", sa.Integer(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=True),
        sa.Column("order", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["match_uid"],
            ["matches.uid"],
            name=op.f("fk_games_match_uid_matches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_games")),
        sa.UniqueConstraint("match_uid", "index", name="ck_game_match_uid_question"),
    )
    op.create_table(
        "rankings",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_uid", sa.Integer(), nullable=False),
        sa.Column("match_uid", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["match_uid"], ["matches.uid"], name=op.f("fk_rankings_match_uid_matches")
        ),
        sa.ForeignKeyConstraint(
            ["user_uid"],
            ["users.uid"],
            name=op.f("fk_rankings_user_uid_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_rankings")),
    )
    op.create_table(
        "questions",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("game_uid", sa.Integer(), nullable=True),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("time", sa.Integer(), nullable=True),
        sa.Column("boolean", sa.Boolean(), server_default="0", nullable=True),
        sa.Column("content_url", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(
            ["game_uid"],
            ["games.uid"],
            name=op.f("fk_questions_game_uid_games"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_questions")),
        sa.UniqueConstraint(
            "game_uid", "position", name="ck_question_game_uid_position"
        ),
    )
    op.create_table(
        "answers",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("question_uid", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("boolean", sa.Boolean(), server_default="0", nullable=True),
        sa.Column("content_url", sa.String(length=256), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "CASE WHEN boolean = 'true' THEN (text = 'True' OR text = 'False') END",
            name=op.f("ck_answers_ck_answers_boolean_text"),
        ),
        sa.ForeignKeyConstraint(
            ["question_uid"],
            ["questions.uid"],
            name=op.f("fk_answers_question_uid_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_answers")),
        sa.UniqueConstraint(
            "question_uid", "text", name="uq_answers_question_uid_text"
        ),
    )
    op.create_table(
        "reactions",
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("create_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_uid", sa.Integer(), nullable=False),
        sa.Column("question_uid", sa.Integer(), nullable=False),
        sa.Column("answer_uid", sa.Integer(), nullable=True),
        sa.Column("open_answer_uid", sa.Integer(), nullable=True),
        sa.Column("user_uid", sa.Integer(), nullable=False),
        sa.Column("game_uid", sa.Integer(), nullable=False),
        sa.Column("dirty", sa.Boolean(), nullable=True),
        sa.Column("answer_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["answer_uid"],
            ["answers.uid"],
            name=op.f("fk_reactions_answer_uid_answers"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["game_uid"],
            ["games.uid"],
            name=op.f("fk_reactions_game_uid_games"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_uid"],
            ["matches.uid"],
            name=op.f("fk_reactions_match_uid_matches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["open_answer_uid"],
            ["open_answers.uid"],
            name=op.f("fk_reactions_open_answer_uid_open_answers"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["question_uid"],
            ["questions.uid"],
            name=op.f("fk_reactions_question_uid_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_uid"],
            ["users.uid"],
            name=op.f("fk_reactions_user_uid_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_reactions")),
        sa.UniqueConstraint(
            "question_uid",
            "answer_uid",
            "user_uid",
            "match_uid",
            "create_timestamp",
            name=op.f("uq_reactions_question_uid"),
        ),
    )


def downgrade():
    op.drop_table("reactions")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("rankings")
    op.drop_table("games")
    op.drop_table("users")
    op.drop_table("open_answers")
    op.drop_table("matches")
