"""empty message

Revision ID: e39a2f27b93f
Revises: 66dc7b13a74b
Create Date: 2020-04-29 22:39:21.923806

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e39a2f27b93f'
down_revision = '66dc7b13a74b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('server_info', sa.Column('prefix', sa.String(length=8), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('server_info', 'prefix')
    # ### end Alembic commands ###
