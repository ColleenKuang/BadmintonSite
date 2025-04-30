"""add updated_at column to Games and PlayGames

Revision ID: ba848f248cc0
Revises: c7f1f5be53cb
Create Date: 2025-04-30 16:14:51.171784

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = 'ba848f248cc0'
down_revision = 'c7f1f5be53cb'
branch_labels = None
depends_on = None

def upgrade():
    # 1. 添加可空字段
    op.add_column('games', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('play_games', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # 2. 填充默认时间
    now = datetime.now(timezone.utc)
    op.execute(sa.text("UPDATE games SET updated_at = :now").bindparams(now=now))
    op.execute(sa.text("UPDATE play_games SET updated_at = :now").bindparams(now=now))

    # 3. 设置为非空（兼容 SQLite）
    with op.batch_alter_table('games') as batch_op:
        batch_op.alter_column('updated_at', nullable=False)

    with op.batch_alter_table('play_games') as batch_op:
        batch_op.alter_column('updated_at', nullable=False)

def downgrade():
    op.drop_column('games', 'updated_at')
    op.drop_column('play_games', 'updated_at')
