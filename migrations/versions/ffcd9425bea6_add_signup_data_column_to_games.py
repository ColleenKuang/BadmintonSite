"""add signup_data column to games

Revision ID: ffcd9425bea6
Revises: c7f1f5be53cb
Create Date: 2025-04-30 01:31:12.468240

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

import json

# revision identifiers, used by Alembic.
revision = 'ffcd9425bea6'
down_revision = 'c7f1f5be53cb'
branch_labels = None
depends_on = None


# migrations/versions/xxx_fix_signup_data.py

def upgrade():
    # 安全添加列
    inspector = sa.inspect(op.get_bind())
    if 'signup_data' not in [col['name'] for col in inspector.get_columns('games')]:
        op.add_column('games', sa.Column('signup_data', sa.JSON(), nullable=True))
    
    # 迁移数据
    conn = op.get_bind()
    games = conn.execute(sa.text("SELECT id FROM games WHERE status = 'READY'")).fetchall()
    
    for (game_id,) in games:
        players = conn.execute(
            sa.text("SELECT DISTINCT player_id FROM play_games WHERE game_id = :id"), 
            {'id': game_id}
        ).fetchall()
        
        if players:
            signups = [{"user_id": pid, "time": str(datetime.utcnow())} for (pid,) in players]
            conn.execute(
                sa.text("UPDATE games SET signup_data = :data WHERE id = :id"),
                {'data': json.dumps(signups), 'id': game_id}
            )
    
    op.alter_column('games', 'signup_data', nullable=False, server_default='[]')

def downgrade():
    op.drop_column('games', 'signup_data')