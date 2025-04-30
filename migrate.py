import json
from datetime import datetime
from sqlalchemy import text
from app import db
from app.models import Users,Gender,Games
def migrate_data(app):
    with app.app_context():
        # 1. 查找所有READY状态的游戏
        ready_games = db.session.execute(
            text("SELECT id FROM games WHERE status = 'ING'")
        ).fetchall()

        for (game_id,) in ready_games:
            game = Games.query.filter_by(id=game_id).first()
            # 2. 从PlayGames获取历史报名数据
            players = db.session.execute(
                text("""
                SELECT DISTINCT player_id 
                FROM play_games 
                WHERE game_id = :game_id
                """), {'game_id': game_id}
            ).fetchall()

            if players:
                signups = []
                for (pid,) in players:
                    user = Users.query.get(pid)
                    # 3. 构建JSON报名数据
                    signups.append({
                        "id": pid, 
                        "username": user.username,
                        "avatar": user.avatar,
                        "gender": 1 if user.gender == Gender.MALE else 0
                    })
                
                # 4. 更新games表
                game.signup_data = json.dumps(signups)
                db.session.commit()
        print(f"迁移完成，处理了 {len(ready_games)} 个游戏")

if __name__ == '__main__':
    from app import app
    migrate_data(app)