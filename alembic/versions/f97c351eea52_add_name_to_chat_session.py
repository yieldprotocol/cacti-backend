"""Add name to chat session

Revision ID: f97c351eea52
Revises: c0f09e7da34d
Create Date: 2023-07-18 14:51:09.383573

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = 'f97c351eea52'
down_revision = 'c0f09e7da34d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chat_session', sa.Column('name', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('chat_session', 'name')
    # ### end Alembic commands ###
