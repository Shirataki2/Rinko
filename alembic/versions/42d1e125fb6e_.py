"""empty message

Revision ID: 42d1e125fb6e
Revises: 9f0c0dbda3ad
Create Date: 2020-05-01 12:21:03.532608

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '42d1e125fb6e'
down_revision = '9f0c0dbda3ad'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('reminder_channel',
                    sa.Column('guild', sa.String(length=64), nullable=False),
                    sa.Column('channel', sa.DateTime(), nullable=False),
                    sa.UniqueConstraint('guild')
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('reminder_channel')
    # ### end Alembic commands ###
