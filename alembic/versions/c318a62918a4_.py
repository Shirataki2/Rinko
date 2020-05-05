"""empty message

Revision ID: c318a62918a4
Revises: c07fc2ca5519
Create Date: 2020-05-05 04:03:14.078955

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c318a62918a4'
down_revision = 'c07fc2ca5519'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('wallet', sa.Column('rotten_turnip', sa.Integer(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('wallet', 'rotten_turnip')
    # ### end Alembic commands ###
