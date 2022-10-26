"""printer ip

Revision ID: s34krt0945kj3
Revises: 5828fdf8867f
Create Date: 2022-09-19 10:28:40.255746

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 's34krt0945kj3'
down_revision = '5828fdf8867f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('printer', sa.Column('ip', sa.String(), nullable=True))
    op.add_column('printer', sa.Column('is_online', sa.Boolean(), nullable=False,
        server_default='f'))
    op.add_column('printer', sa.Column('is_virtual', sa.Boolean(), nullable=False,
        server_default='f'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('printer', 'ip')
    op.drop_column('printer', 'is_online')
    op.drop_column('printer', 'is_virtual')
    # ### end Alembic commands ###
