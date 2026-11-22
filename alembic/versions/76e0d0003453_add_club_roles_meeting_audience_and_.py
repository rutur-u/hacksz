"""add club roles meeting audience and club news

Revision ID: 76e0d0003453
Revises: ce10de507c17
Create Date: 2026-11-22 15:24:19.291255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76e0d0003453'
down_revision: Union[str, Sequence[str], None] = 'ce10de507c17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SQLite batch mode recreates tables; stable names keep reflection deterministic.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('class_memberships',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('class_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.Enum('member', 'visitor', name='club_role', native_enum=False, length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['class_id'], ['extra_classes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('class_id', 'user_id', name='uq_class_memberships_person')
    )
    with op.batch_alter_table('class_memberships', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_class_memberships_class_id'), ['class_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_class_memberships_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_class_memberships_user_role', ['user_id', 'role'], unique=False)

    # Existing slots become open to everyone so nobody loses their schedule.
    with op.batch_alter_table(
        'class_meetings', schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.add_column(sa.Column(
            'audience',
            sa.Enum('everyone', 'members', name='meeting_audience', native_enum=False, length=20),
            nullable=False,
            server_default=sa.text("'everyone'"),
        ))

    # Existing posts stay public campus news (no club, public audience).
    with op.batch_alter_table(
        'news_posts', schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.add_column(sa.Column('class_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column(
            'audience',
            sa.Enum('public', 'members', name='news_audience', native_enum=False, length=20),
            nullable=False,
            server_default=sa.text("'public'"),
        ))
        batch_op.create_index(batch_op.f('ix_news_posts_class_id'), ['class_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_news_posts_class_id_extra_classes',
            'extra_classes',
            ['class_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        'news_posts', schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint('fk_news_posts_class_id_extra_classes', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_news_posts_class_id'))
        batch_op.drop_column('audience')
        batch_op.drop_column('class_id')

    with op.batch_alter_table(
        'class_meetings', schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_column('audience')

    with op.batch_alter_table('class_memberships', schema=None) as batch_op:
        batch_op.drop_index('ix_class_memberships_user_role')
        batch_op.drop_index(batch_op.f('ix_class_memberships_user_id'))
        batch_op.drop_index(batch_op.f('ix_class_memberships_class_id'))

    op.drop_table('class_memberships')
