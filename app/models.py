from app import db, login
from flask_login import UserMixin 
from enum import Enum
from sqlalchemy import func, select, and_, case, event, PrimaryKeyConstraint, CheckConstraint, text
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
import pandas as pd
import csv
from datetime import datetime, timezone
class Gender(Enum):
    MALE = "male"
    FEMALE = "female"

class GameStatus(Enum):
    READY = 0
    ING = 1
    DONE = 2
    ERR = 3
    
class TeamType(Enum):
    HOME_TEAM = 0
    AWAY_TEAM = 1

class MatchType(Enum):
    MIX_DOUBLE = "mix_double"
    WOMEN_DOUBLE = "women_double"
    MEN_DOUBLE = "men_double"
    WOMEN_SINGLE = "women_single"
    MEN_SINGLE = "men_single"
    SINGLE = "single"
    
class MatchResultType(Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"

class Users(UserMixin, db.Model): 
    # __tablename__ = 'users' # 如果不显式声明，表名将会根据类名自动生成全小写处理
    id = db.Column(db.Integer, unique=True, primary_key=True) 
    username = db.Column(db.String(80),  nullable=False)
    gender = db.Column(db.Enum(Gender), nullable=False)
    password = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(120))  # 存储头像文件名
    
    # played_games = db.relationship("PlayGames", backref=db.backref('player', lazy=True))
    def __repr__(self):
        return "<User {} {} {}>".format(self.username,self.gender,self.avatar)
    
# 1. 用户对象加载
# 当用户登录后，Flask-Login 会在会话（Session）中存储用户的唯一标识符（如 user_id）。
# 在后续的请求中，@login.user_loader 装饰的函数会被调用，
# 通过这个 user_id 从数据库或其他存储中加载完整的用户对象，供后续逻辑使用。

# 2. 维持登录状态
# 每次请求时，Flask-Login 都会通过用户加载器验证用户是否存在且有效。
# 如果用户存在，则保持登录状态；如果不存在，则自动清除会话，要求重新登录。
@login.user_loader
def load_user(user_id):
    return Users.query.filter_by(id=user_id).first()


class Games(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True) 
    creator_id = db.Column(db.Integer,nullable=False)
    game_type = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(50), default = "")
    status = db.Column(db.Enum(GameStatus), default = GameStatus.READY)
    title = db.Column(db.String(50), default = "")
    rule = db.Column(db.String(100), default = "")
    signup_data = db.Column(db.JSON, default=list)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc))
    
    def __repr__(self):
        return "<Game-{}-{}-{} Admin:{} Time:{} Location:{} Rule:{} Signed_data:{}>".format(self.id, self.title, self.game_type, self.creator_id, self.timestamp, self.location, self.rule, self.signup_data)

class PlayGames(db.Model):
    __table_args__ = (
        # 加速按比赛+选手的查询
        db.Index('idx_game_player', 'game_id', 'player_id'),
        # 加速按比赛+场次+队伍的查询
        db.Index('idx_game_match_team', 'game_id', 'match_idx', 'team'),
    )
    # 独立自增主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # 外键字段（不再作为主键）
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 其他字段
    match_idx = db.Column(db.Integer, nullable=False)
    match_type = db.Column(db.Enum(MatchType), nullable=False)
    team = db.Column(db.Enum(TeamType), nullable=False)
    score = db.Column(db.Integer,nullable=True,)
    net_score = db.Column(db.Integer,nullable=True,)
    result = db.Column(db.Enum(MatchResultType),nullable=True,)
    
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda:datetime.now(timezone.utc), onupdate=lambda:datetime.now(timezone.utc))
    
    # 定义与用户和比赛的关系（便于ORM查询）
    player = db.relationship('Users', backref='played_games')
    match = db.relationship('Games', backref='participants')
    
    def __repr__(self):
        return "<PlayGames {}-{} team-{} player_id-{} score:{} >\n".format(self.game_id, self.match_idx, self.team,self.player_id,self.score)
    
def get_player_stats(player_id: str, game_id: str) -> dict:
    # print("get_player_stats")
    # print(player_id)
    # print(game_id)
    try:
        # 定义聚合表达式
        win_cnt = func.count(
            case(
                (and_(
                    PlayGames.result == MatchResultType.WIN,
                    PlayGames.game_id == game_id,
                    PlayGames.player_id == player_id
                ), 1),
                else_=None
            )
        ).label('win_cnt')

        loss_cnt = func.count(
            case(
                (and_(
                    PlayGames.result == MatchResultType.LOSS,
                    PlayGames.game_id == game_id,
                    PlayGames.player_id == player_id
                ), 1),
                else_=None
            )
        ).label('loss_cnt')

        total_net_score = func.coalesce(
            func.sum(
                case(
                    (and_(
                        PlayGames.game_id == game_id,
                        PlayGames.player_id == player_id
                    ), PlayGames.net_score),
                    else_=0
                )
            ), 
            0
        ).label('net_score')

        # 执行单次查询
        result = db.session.query(
            win_cnt,
            loss_cnt,
            total_net_score
        ).first()

        # 处理查询结果
        return {
            "player_id": player_id,
            "win_cnt": result.win_cnt if result else 0,
            "loss_cnt": result.loss_cnt if result else 0,
            "net_score": result.net_score if result else 0
        }

    except SQLAlchemyError as e:
        print(f"数据库查询失败: {str(e)}")
        return {
            "player_id": player_id,
            "win_cnt": 0,
            "loss_cnt": 0,
            "net_score": 0
        }
 
class GameHistory(db.Model):
    __table_args__ = (
        PrimaryKeyConstraint('game_id', 'player_id', name="uq_game_player"),
        CheckConstraint('ranking >= 1', name='check_ranking_positive'),
        CheckConstraint('win_cnt >= 0 AND loss_cnt >= 0', name='check_win_loss')
    )
    
    # modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    net_score = db.Column(db.Integer,nullable=False,)
    ranking = db.Column(db.Integer,nullable=False,)
    win_cnt = db.Column(db.Integer,nullable=False,)
    loss_cnt = db.Column(db.Integer,nullable=False,)
    def __repr__(self):
        return "<GameHistory Game_id{} player_id-{} rank{} win-loss:{}-{}>\n".format(self.game_id,self.player_id,self.ranking,self.win_cnt,self.loss_cnt)
    
def get_game_scores(user_id, game_id):
    matches = db.session.query(
                    PlayGames.match_idx,
                    PlayGames.score,
                    PlayGames.net_score
                ).filter(
                    PlayGames.player_id==user_id,
                    PlayGames.game_id==game_id
                ).all()

    re = {
        "matches_indices":[],
        "score":[],
        "net_score":[]
    }
    
    for m in matches:
        re["matches_indices"].append(m[0])
        re["score"].append(m[1])
        re["net_score"].append(m[2])
        
    
    return pd.DataFrame(re)  
      
def create_game_with_csv(
    file_path: str,
    creator_id: int,
):
    """
    创建新Game并关联导入PlayGames数据
    
    参数:
    file_path: PlayGames数据CSV路径
    creator_id: 游戏创建者ID (必需)
    gametype: 游戏类型 (必需)
    gamemode: 游戏模式 (必需)
    location: 游戏地点 (可选)
    status: 游戏状态 (可选)
    """
    try:
        # ===================== 第一阶段：创建Game记录 =====================
        new_game = Games(
            creator_id=creator_id,
            game_type="double-1",
            status=GameStatus.DONE,
        )
        
        db.session.add(new_game)
        db.session.flush()# 获取新Game的ID但不提交事务
        
        print(f"创建Game记录 ID: {new_game.id}")
        # ===================== 第二阶段：导入PlayGames数据 =====================
        with open(file_path, 'r', encoding='utf_8_sig') as f:
            reader = list(csv.DictReader(f))  # 转换为列表
            total_rows = len(reader)
            play_games_to_add = []
            
            for row_num in range(total_rows):
                row = reader[row_num]
                print("row_num:{}".format(row_num),end=" ")
                try:
                    # 数据验证
                    required_fields = ['player_id', 'match_idx', 'score']
                    if any(field not in row for field in required_fields):
                        raise ValueError(f"第{row_num}行缺少必要字段")
                    
                    team = TeamType.HOME_TEAM
                    if (row_num % 4 == 2) or (row_num % 4 == 3):
                        team = TeamType.AWAY_TEAM
                    
                    teammate_row = row_num
                    if row_num % 2 == 1:
                        teammate_row = reader[row_num - 1]
                    else:
                        teammate_row = reader[row_num + 1]
                    teammate_id = int(teammate_row['player_id'])
                    my_gender = Users.query.filter(Users.id == int(row['player_id'])).first().gender
                    teammate_gender = Users.query.filter(Users.id == int(teammate_id)).first().gender
                    mt = MatchType.MIX_DOUBLE if my_gender != teammate_gender else MatchType.MEN_DOUBLE if my_gender==Gender.MALE else MatchType.WOMEN_DOUBLE
                    result = MatchResultType.WIN
                    if (row_num % 4 == 0) or (row_num % 4 == 1): #home
                        print("home opponent row {}.".format(row_num + 2), end=" ")
                        opponent_row = reader[row_num + 2]
                    if (row_num % 4 == 2) or (row_num % 4 == 3): #away
                        print("away opponent row {}.".format(row_num - 2), end=" ")
                        opponent_row = reader[row_num - 2]
                        
                    
                    net_score = int(row["score"]) - int(opponent_row["score"])
                    result = MatchResultType.WIN if net_score > 0 else MatchResultType.LOSS
                    
                    # 构造PlayGame记录
                    play_game = PlayGames(
                        game_id=new_game.id,
                        player_id=int(row['player_id']),
                        match_idx=int(row['match_idx']),
                        match_type=mt,
                        team=team,
                        score=int(row['score']) if row.get('score') else 0,
                        result=result,
                        net_score=net_score
                    )
                    print(play_game)
                    play_games_to_add.append(play_game)
                    
                except KeyError as e:
                    db.session.rollback()
                    print(f"PlayGames第{row_num}行字段错误: {str(e)}")
                    return
                except ValueError as e:
                    db.session.rollback()
                    print(f"PlayGames第{row_num}行数值错误: {str(e)}")
                    return

            # 批量插入
            db.session.bulk_save_objects(play_games_to_add)
            db.session.commit()
            print(f"""
                导入成功！
                新建Game ID: {new_game.id}
                关联{len(play_games_to_add)}条PlayGames记录
                """)

        return new_game.id
    except IntegrityError as e:
        db.session.rollback()
        print(f"数据冲突已回滚: {str(e)}")
    except Exception as e:
        db.session.rollback()
        print(f"系统错误已回滚: {str(e)}")

def find_good_partner(my_id):
    # 首先找到当前用户参加的所有比赛和场次组合
    print(f"当前查询的用户id:{my_id}")
    # 1. 找出 current_user_id 参加的所有比赛场次
    user_matches = db.session.query(
        PlayGames.game_id,
        PlayGames.match_idx,
        PlayGames.team
    ).filter(
        PlayGames.player_id == my_id
    ).subquery()

    # 2. 计算每个队友的胜率
    teammates = db.session.query(
        PlayGames.player_id,
        Users.username,
        func.count(PlayGames.id).label('total_matches_with_me'),  # 组队次数
        func.sum(case((PlayGames.result == MatchResultType.WIN, 1), else_=0)).label('wins_with_me'),  # 胜场数
        func.round(
            func.sum(case((PlayGames.result == MatchResultType.WIN, 1), else_=0)) / 
            func.nullif(func.count(PlayGames.id), 0) 
        ,2).label('win_rate'), # 胜率
        func.round(func.avg(PlayGames.net_score), 2).label('avg_net_score') # 组队时的平均净得分
    ).join(
        user_matches,
        and_(
            PlayGames.game_id == user_matches.c.game_id,
            PlayGames.match_idx == user_matches.c.match_idx,
            PlayGames.team == user_matches.c.team  # 同队
        )
    ).join(
        Users,
        PlayGames.player_id == Users.id
    ).filter(
        PlayGames.player_id != my_id  # 排除自己
    ).group_by(
        PlayGames.player_id,
        Users.username
    ).having(
        func.count(PlayGames.id) >= 3  # 只统计组队3次以上的队友
    ).order_by(
        text('win_rate DESC'), # 优先按胜率排序
        text('avg_net_score DESC'), # 胜率相同按平均净得分排序
        text('total_matches_with_me DESC') # 最后按组队次数排序
    ).all()
    
    return teammates

def find_best_opponent(my_id):
    print(f"当前查询的用户id:{my_id}")
    # 1. 找出 current_user_id 参加的所有比赛场次
    user_matches = db.session.query(
        PlayGames.game_id,
        PlayGames.match_idx,
        PlayGames.team
    ).filter(
        PlayGames.player_id == my_id
    ).subquery()

    # 2. 计算每个对手的统计数据
    opponents = db.session.query(
        PlayGames.player_id,
        Users.username,
        func.sum(case((PlayGames.result == MatchResultType.WIN, 1), else_=0)).label('wins_against_me'),
        # 胜率保留2位小数（ROUND(胜场数/总场数, 2)）
        func.round(
            func.sum(case((PlayGames.result == MatchResultType.WIN, 1), else_=0)) / 
            func.nullif(func.count(PlayGames.id), 0) 
        ,2).label('win_rate'), # 胜率
        # 平均净胜分保留2位小数（ROUND(AVG(net_score), 2)）
        func.round(func.avg(PlayGames.net_score), 2).label('avg_net_score'),
        func.count(PlayGames.id).label('total_matches_against_me'),
    ).join(
        user_matches,
        and_(
            PlayGames.game_id == user_matches.c.game_id,
            PlayGames.match_idx == user_matches.c.match_idx,
            PlayGames.team != user_matches.c.team  # 不同队伍
        )
    ).join(
        Users,
        PlayGames.player_id == Users.id
    ).filter(
        PlayGames.player_id != my_id  # 排除自己
    ).group_by(
        PlayGames.player_id,
        Users.username
    ).order_by(
        text('win_rate DESC'), # 先按赢我的次数排序
        text('avg_net_score DESC'), # 再按净胜分排序
        text('wins_against_me DESC'), # 先按赢我的次数排序
        text('total_matches_against_me DESC') # 最后按对局数排序   
    ).all()
    
    return opponents
# 使用示例
# if __name__ == '__main__':
#     pass
#     从Flask-SQLAlchemy3.0开始，
#     所有对db.engine和db.session的访问都要一个活动的Flask应用程序上下文
#     with app.app_context():
#         # 删除所有继承自db.Model的表
#         db.drop_all()
#         # 创建所有继承自db.Model的表
#         db.create_all()
# 查询前刷新会话
#  db.session.expire_all()
#  db.session.query(PlayGames).delete()

# db.metadata.drop_all(
#     bind=db.engine,
#     tables=[PlayGames.__table__],  # 明确指定要删除的表
#     checkfirst=True  # 如果表不存在则跳过
# )

# flask db stamp head - Alembic 的命令，它用于将数据库的版本标记为当前迁移的最新版本（即“head”）
# 你已经手动执行了迁移脚本，或在数据库中做了一些修改，但迁移版本和数据库的版本记录不同步时，可以用它来修复。

