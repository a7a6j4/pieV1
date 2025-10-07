"""empty message

Revision ID: e44ffb081aaa
Revises: b4a3ecb5bab7
Create Date: 2025-08-16 13:11:47.522011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e44ffb081aaa'
down_revision: Union[str, Sequence[str], None] = 'b4a3ecb5bab7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass

def downgrade() -> None:
    pass