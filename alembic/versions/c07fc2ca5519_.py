"""empty message

Revision ID: c07fc2ca5519
Revises: 8a44839319fb
Create Date: 2020-05-05 03:39:36.077468

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c07fc2ca5519'
down_revision = '8a44839319fb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('turnip',
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('date', sa.DateTime(), nullable=False)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('turnip')
    # ### end Alembic commands ###
