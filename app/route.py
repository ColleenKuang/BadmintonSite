from flask import render_template, redirect, flash, url_for, request, session, jsonify, current_app, abort
from app import app, db, bcrypt, cors, Config, double_event_list, single_event_list, team_event_list
from app.forms import RegisterForm, LoginForm
from app.models import Users, Games, PlayGames, GameHistory
from app.models import Gender, TeamType, MatchResultType, GameStatus, MatchType
from app.models import get_player_stats, get_game_scores, create_game_with_csv, find_good_partner, find_best_opponent
from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.utils import secure_filename
import os, json
from app.games import double_mode_1, double_mode_2, double_mode_3
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
from sqlalchemy import and_, desc
from datetime import datetime, timezone
import pytz 
# app.route(rule, options)装饰器
# rule - 函数绑定对应的URL
# options - 转发给基础Rule对此那个的参数列表
@app.route("/")
# 注册一个处理函数，这个函数是处理某个请求的处理函数（Flask 官方把它叫做视图函数view funciton）
# 一个视图函数也可以绑定多个 URL
@app.route("/index")
@login_required
def hello_world():
    # TODO tell fortune
    gps = find_good_partner(current_user.id)
    # print(gps)
    bos = find_best_opponent(current_user.id)
    # print(bos)
    return render_template('index.html',gps=list(gps),bos=list(bos))

@app.route('/register', methods=['GET','POST'])
def register():        
    form = RegisterForm()
    if form.validate_on_submit():
        validation_errors = form.validate_register()
        if validation_errors:
            flash(validation_errors, category="danger")
            return redirect(url_for("register"))
        
        try:
            # Create user
            user = Users(
                username=form.username.data,
                password=bcrypt.generate_password_hash(form.password.data),
                gender=Gender.MALE if form.gender.data == "1" else Gender.FEMALE
            )
            
            db.session.add(user)
            db.session.flush()  # Get user ID without commit
            
            # Handle avatar
            file = request.files.get('avatar')
            if file and file.filename:
                if not Config.allowed_pic_file(file.filename):
                    flash("Invalid file type", "danger")
                    return redirect(url_for("register"))
                    
                if file.content_length > Config.MAX_CONTENT_LENGTH:
                    flash("File too large", "danger")
                    return redirect(url_for("register"))
                    
                filename = secure_filename(Config.unique_filename(file.filename))
                os.makedirs(Config.AVATAR_FOLDER, exist_ok=True)
                file.save(os.path.join(Config.AVATAR_FOLDER, filename))
                user.avatar = filename
            
            db.session.commit()
            flash("Registration successful!", "success")
            return redirect(url_for("login"))
            
        except IntegrityError:
            db.session.rollback()
            flash("Username already exists", "danger")
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Registration failed")
            flash("Registration failed, please try again", "danger")
        
    return render_template("register.html",form = form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 已登录用户重定向
    if current_user.is_authenticated:
        return redirect(url_for('hello_world'))
    
    form = LoginForm()
    
    # 仅处理POST请求（更安全）
    if request.method == 'POST':
        # 注册按钮处理
        if 'register_btn' in request.form:
            return redirect(url_for('register'))
        
        # 登录按钮处理
        if 'login_btn' in request.form:
            # 前端非空检查（基础验证）
            if not form.username.data or not form.password.data:
                flash("用户名和密码不能为空", category='danger')
                return render_template("login.html", form=form)
            
            # WTForms完整验证
            if form.validate():
                user = Users.query.filter_by(username=form.username.data).first()
                
                # 用户存在性检查
                if not user:
                    flash("用户不存在，请先注册", category='danger')
                    return redirect(url_for('register'))
                
                # 密码验证（带防时序攻击）
                try:
                    if not bcrypt.check_password_hash(user.password, form.password.data):
                        flash("密码错误", category='danger')
                        # 记录失败尝试（安全审计）
                        # current_app.logger.warning(f"Failed login attempt for user: {form.username.data}")
                        return render_template("login.html", form=form)
                except ValueError as e:
                    # current_app.logger.error(f"Password hash error: {str(e)}")
                    flash("系统错误，请稍后再试", category='danger')
                    return render_template("login.html", form=form)
                
                # 登录成功
                login_user(user, remember=form.remember.data)
                
                # 安全的重定向处理
                next_page = request.args.get('next')
                if next_page:
                    # 验证next参数是否安全
                    if not is_safe_url(next_page):
                        return abort(400)
                    return redirect(next_page)
                return redirect(url_for('hello_world'))
            
            # 表单验证失败
            flash("请检查输入内容", category='danger')
    
    return render_template("login.html", form=form)

# 安全URL检查函数
def is_safe_url(target):
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

@app.route("/logout")
def logout():
    # 清空所有 Session 数据
    session.clear()
    logout_user()
    return redirect(url_for('login'))

@app.route("/gamemenu")
@login_required
def gamemenu():
    render_card = app.jinja_env.get_template("macros.html").module.render_card
    tabmenu = [
        {
           'tabname': "double",
           'tabshowname': "双打",
           'tabcontent': render_card(double_event_list)
        },
        {
           'tabname': "single",
           'tabshowname': "单打",
           'tabcontent': render_card(single_event_list)
        },
        {
           'tabname': "team",
           'tabshowname': "团队",
           'tabcontent': render_card(team_event_list)
        },
        
        ]
    
    return render_template("gamemenu.html",tabmenu=tabmenu)

@app.route('/api/create_game', methods=['POST'])
@login_required
def create_game():
    # 验证请求数据
    data = request.get_json()
    if not data or 'game_type' not in data or 'title' not in data:
        return jsonify({"status": "error", "msg": "无效的请求参数"}), 400

    # 创建新游戏记录
    try:
        new_game = Games(
            game_type=data['game_type'],
            creator_id=current_user.id,
            signup_data=json.dumps([""] * 6)
        )
        
        db.session.add(new_game)
        db.session.commit()
        
        session['game_id'] = new_game.id
        session["game_active_tab_idx"] = 1
        return jsonify({
            "status": "success",
            "game_id": new_game.id,
            "msg": "比赛创建成功"
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "msg": f"数据库错误: {str(e)}"
        }), 500

@app.route('/api/remove_game', methods=['POST'])
@login_required
def remove_game():
    try:
        print("current id: {} admin_id:{}".format(current_user.id,session["game_config"]["admin"]["id"]))
        if current_user.id != session["game_config"]["admin"]["id"]:
            return jsonify({"status": "success","msg":"你不是管理员，无权限删除"}), 200
        
        
        PlayGames.query.filter_by(game_id=session["game_id"]).delete()
        Games.query.filter_by(id=session["game_id"]).delete()
        db.session.commit()
        
        session.pop('game_config', None)
        
        return jsonify({"status": "success"}), 200
    except KeyError as e:
        print(f"未找到游戏ID: {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 400
    except Exception as e:
        print(f"Game移除错误: {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 400

@app.route('/api/update_member', methods=['POST'])
def update_member():      
    try:
        data = request.get_json()
        print("update_member",data)
        session["game_active_tab_idx"] = 1
        # Step 1. 预先检查
        game = Games.query.filter_by(id=session['game_id']).first()
        client_updated_at = datetime.fromisoformat(data['client_updated_at'])
        if (client_updated_at != game.updated_at):
            return jsonify({"status": "success","msg":"数据已被其他用户修改,请刷新页面"}), 200
        
        if session["game_config"]["gamestatus"] == GameStatus.DONE.value:
            return jsonify({"status": "success","msg":"比赛已完结不可修改"}), 200
        
        # Step 2. 分情况处理
        # add quota
        if data['action'] == 'add':
            print(data['action'])
            if(data['gametype'] in ['double-1']):
                session["game_config"]["member_list"].append("")
            elif(data['gametype'] in ['double-2','double-3']):
                session["game_config"]["member_list"].append("")
                session["game_config"]["member_list"].append("")
        # minus quota
        if data['action'] == 'minus':
            if len(session["game_config"]["member_list"]) == 4:
                return jsonify({"status": "success","msg": "不能少于4人"}), 200
            
            if(data['gametype'] in ['double-1']):
                idx = len(session["game_config"]["member_list"]) - 1
                while(session["game_config"]["member_list"][idx] != ""):
                    if (idx < 0): break
                    idx -= 1
                if idx < 0:
                    return jsonify({"status": "success","msg": "当前满人不可减少位置"}), 200   
                else:
                    for i in range(idx,len(session["game_config"]["member_list"])-1):
                        session["game_config"]["member_list"][i] = session["game_config"]["member_list"][i+1]
                session["game_config"]["member_list"].pop()
            
            elif(data['gametype'] in ['double-2','double-3']):
                if (session["game_config"]["member_list"][-1] != "") or (session["game_config"]["member_list"][-2] != ""):
                    return jsonify({"status": "success","msg": "最后一行存在报名人员，操作失败"}), 200
                session["game_config"]["member_list"].pop()
                session["game_config"]["member_list"].pop()
        
        idx = int(data.get("selected_idx", 0))
        # 检查索引是否越界
        if idx >= len(session["game_config"]["member_list"]):
            return jsonify({"status": "error", "msg": "索引越界"}), 400

        if data['action'] == 'cancel':
            session["game_config"]["member_list"][idx] = ""
            
        memberlist = [d["id"] for d in session["game_config"]["member_list"] if isinstance(d,dict)]
        if data['action'] == 'self':    
            if (current_user.id in memberlist):
                print("user already exist.")
                return jsonify({"status": "success","msg": "用户已存在"}), 200
            session["game_config"]["member_list"][idx] = {"id":current_user.id, 
                                                          "avatar":current_user.avatar,
                                                          "username":current_user.username,
                                                          "gender":1 if current_user.gender == Gender.MALE else 0}
        
        if data['action'] == 'other':  
            new_members = [Users.query.filter_by(id=int(user_id)).first() for user_id in data["selected_ids"] if Users.query.filter_by(id=int(user_id)).first().id not in memberlist]
            print(new_members) 
            if len(new_members) == 1:
                other = new_members[0]
                session["game_config"]["member_list"][idx] = {"id":other.id, 
                                                                "avatar":other.avatar,
                                                                "username":other.username,
                                                                "gender":1 if other.gender == Gender.MALE else 0}
            else:
                idx = 0
                for other in new_members:
                    while(session["game_config"]["member_list"][idx] != ""):
                        idx += 1
                    if idx >= len(session["game_config"]["member_list"]):
                        return jsonify({"status": "error", "msg": "选择人数超过可添加的人员数目"}), 400
                    session["game_config"]["member_list"][idx] = {"id":other.id, 
                                                                "avatar":other.avatar,
                                                                "username":other.username,
                                                                "gender":1 if other.gender == Gender.MALE else 0}
                    idx += 1
        
        
        # 汇总处理结果存到数据库里
        game.signup_data = json.dumps(session["game_config"]["member_list"])
        if session["game_config"]["gamestatus"] == GameStatus.ING.value or session["game_config"]["gamestatus"] == GameStatus.ERR.value:
            game.status = GameStatus.ERR
            session.modified = True
            db.session.commit()
            return jsonify({"status": "success","msg":"比赛正在进行，有人员更改，需要重新生成对局"}), 200
        
        session.modified = True
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"status": "error","msg": str(e)}), 500

@app.route('/api/choose_game', methods=['POST'])
def choose_game():
    try:
        data = request.get_json()
        session['game_id'] = int(data["game_id"])
        session["game_active_tab_idx"] = 1
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# TODO modify PlayGame records into one
def record_double_schedule(schedule):
    games = []
    # print("record")
    for idx, g in enumerate(schedule):
        # print(g)
        t00 = session["game_config"]["member_list"][g[0][0]]
        t01 = session["game_config"]["member_list"][g[0][1]]
        t10 = session["game_config"]["member_list"][g[1][0]]
        t11 = session["game_config"]["member_list"][g[1][1]]
        ht_match_type = MatchType.MIX_DOUBLE if t00["gender"] != t01["gender"] else MatchType.MEN_DOUBLE if t00["gender"] == 1 else MatchType.WOMEN_DOUBLE
        at_match_type = MatchType.MIX_DOUBLE if t10["gender"] != t11["gender"] else MatchType.MEN_DOUBLE if t11["gender"] == 1 else MatchType.WOMEN_DOUBLE
        current_time = datetime.now(timezone.utc)
        records_to_add = [
            PlayGames(
                match_idx = idx,
                player_id = t00["id"],
                game_id = session['game_id'],
                team = TeamType.HOME_TEAM,
                match_type = ht_match_type,
                score = 0,
                updated_at=current_time
            ),
            PlayGames(
                match_idx = idx,
                player_id = t01["id"],
                game_id = session['game_id'],
                team = TeamType.HOME_TEAM,
                match_type = ht_match_type,
                score = 0,
                updated_at=current_time
            ),
            PlayGames(
                match_idx = idx,
                player_id = t10["id"],
                game_id = session['game_id'],
                team = TeamType.AWAY_TEAM,
                match_type = at_match_type,
                score = 0,
                updated_at=current_time
            ),
            PlayGames(
                match_idx = idx,
                player_id = t11["id"],
                game_id = session['game_id'],
                team = TeamType.AWAY_TEAM,
                match_type = at_match_type,
                score = 0,
                updated_at=current_time
            )
        ]
        # print(records_to_add)
        db.session.bulk_save_objects(records_to_add)
        db.session.commit()
        games.append({
            "home_team": [t00,t01],
            "away_team": [t10,t11],
            "score": [0,0]
        })
    return games

# TODO record_single_schedule
def record_single_schedule(schedule):
    pass

@app.route('/api/generate_matches', methods=['POST'])
def generate_matches():
    # ---------- 数据验证 ----------
    # 1. 检查当前game的状态
    if session["game_config"]["gamestatus"] == GameStatus.DONE.value:
            return jsonify({"status": "success","msg":"比赛已完结不可修改"}), 200
        

    # 2. 检查必要字段
    data = request.get_json()
    required_fields = ['matchesPerPlayer']
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "msg": f"缺少必填字段 {field}"}), 400

    # 3. 验证数值类型
    try:
        matchesPerPlayer = int(data["matchesPerPlayer"])
    except (ValueError, TypeError):
        return jsonify({"status": "error", "msg": "人均局数要为正整数"}), 400

    # 4. 验证数值范围
    if matchesPerPlayer <= 0:
        return jsonify({"status": "error", "msg": "人均局数要为正数"}), 400
    
    # ---------- 数据录入 ----------
    try:        
        deleted_count = PlayGames.query.filter(
            getattr(PlayGames, "game_id") == session['game_id']
        ).delete()
        print("del count:",deleted_count)
        db.session.commit()
        
        if session["game_config"]["gametype"] == "double-1":
            re = double_mode_1(session['game_config']["member_list"], matches_per_player=matchesPerPlayer)
        if session["game_config"]["gametype"] == "double-2":
            re = double_mode_2(session['game_config']["member_list"], matches_per_player=matchesPerPlayer)
        if session["game_config"]["gametype"] == "double-3":
            re = double_mode_3(session['game_config']["member_list"], matches_per_player=matchesPerPlayer)
        # print("schedule:",re)
        if isinstance(re,str):
            return jsonify({"status": "success","msg":re}), 200
        
        if session["game_config"]["gametype"].split('-')[0] == "double":
            session["game_config"]["games"] = record_double_schedule(re)
        session["game_config"]["games_progress"] = [0] * len(session["game_config"]["games"])
        session["game_active_tab_idx"] = 2
        session["game_config"]["ranking"] = []
        if session["game_config"]["gamestatus"] == GameStatus.ERR.value:
            game = Games.query.filter_by(id=session['game_id']).first()
            game.status = GameStatus.READY
            db.session.commit()
            
        session.modified = True
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({"status": "error", "msg": str(e)}), 500

def player_ranking(game_id,member_list):
    ranking = []
    for m in member_list:
        if m == "": continue
        re = get_player_stats(player_id=m["id"], game_id=game_id)
        ranking.append({
            "player_id": re["player_id"],
            "player_name": m["username"],
            "player_avatar": m["avatar"],
            "win_cnt": re["win_cnt"],
            "loss_cnt": re["loss_cnt"],
            "net_score": re["net_score"],
        })
    
    ranking.sort(
            key=lambda player: (-player["win_cnt"], -player["net_score"])
        )

    return ranking

@app.route('/api/update_score', methods=['POST'])
def update_score():
    data = request.get_json()
    print("update_score:", data)
    
    # ---------- 数据验证 ----------
    # 0. 检查游戏状态
    if session["game_config"]["gamestatus"] == GameStatus.ERR.value:
        return jsonify({"status": "success","msg":"比赛设置异常，请重新生成对局"}), 200
    
    # 1. 检查必要字段
    required_fields = ['home', 'away', 'match_idx']
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "msg": f"缺少必填字段 {field}"}), 400

    # 2. 验证数值类型
    try:
        home_score = int(data['home'])
        away_score = int(data['away'])
    except (ValueError, TypeError):
        return jsonify({"status": "error", "msg": "分数必须为整数"}), 400

    # 3. 验证数值范围
    if home_score < 0 or away_score < 0:
        return jsonify({"status": "error", "msg": "分数不能为负数"}), 400

    # 4. 羽毛球规则校验
    if (home_score >= 21 or away_score >= 21) and abs(home_score - away_score) < 2:
        return jsonify({"status": "error", "msg": "21分后需净胜2分"}), 400

    if (home_score > 30 or away_score > 30) or (home_score == 30 and away_score == 29):
        return jsonify({"status": "error", "msg": "单局最高30分"}), 400

    if home_score == away_score:
        return jsonify({"status": "error", "msg": "比分不能相同"}), 400
        
    # ---------- 数据录入 ----------
    try:
        client_updated_at = datetime.fromisoformat(data['client_updated_at'])
        current_time = datetime.now(timezone.utc)
        updated_rows = PlayGames.query.filter_by(
            game_id=session['game_id'],
            match_idx=data['match_idx'],
            team=TeamType.HOME_TEAM,
            updated_at = client_updated_at
        ).update({
            "score": home_score,
            "net_score": (home_score - away_score),
            "result": MatchResultType.WIN if (home_score > away_score) else MatchResultType.LOSS.name,
            "updated_at": current_time
        }, synchronize_session=False)
        db.session.commit()
        # print(f"批量更新 {updated_rows} 条记录")
        if updated_rows == 0:
            exists = PlayGames.query.filter_by(
                game_id=session['game_id'],
                match_idx=data['match_idx'],
                team=TeamType.HOME_TEAM,
            )
            
            if exists:
                return jsonify({"status": "success","msg":"数据已被其他用户修改,请刷新页面"}), 200
        
        updated_rows = PlayGames.query.filter_by(
            game_id=session['game_id'],
            match_idx=data['match_idx'],
            team=TeamType.AWAY_TEAM,
            updated_at = client_updated_at
        ).update({
            "score": away_score,
            "net_score": (away_score - home_score),
            "result": MatchResultType.WIN if away_score > home_score else MatchResultType.LOSS,
            "updated_at": current_time
        }, synchronize_session=False)
        db.session.commit()
        # print(f"批量更新 {updated_rows} 条记录")
            
        session["game_config"]["games"][int(data['match_idx'])]["score"] = [home_score, away_score]
        session["game_active_tab_idx"] = 2
        session["game_config"]["games_progress"][int(data['match_idx'])] = 1
        
        # 每次更新分数，就重新计算一次排名
        re = update_ranking()
        if re[1] == 200:
            game = Games.query.filter_by(id=session['game_id']).first()
            game.status = GameStatus.ING
            db.session.commit()
            session.modified = True
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "msg": re[0].get_json()["msg"]}), re[1]
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"数据库错误: {str(e)}")
        return jsonify({"status": "error", "msg": "数据库操作失败"}), 500

    except KeyError as e:
        print(f"Session 数据异常: {str(e)}")
        return jsonify({"status": "error", "msg": "比赛信息丢失"}), 400

@app.route('/api/update_ranking', methods=['POST'])
def update_ranking():
    try: 
        data = request.get_json()
        try:
            session["game_config"]["ranking"] = player_ranking(session['game_id'],session["game_config"]["member_list"])
        except Exception as e:
            print(f"Game Status Update Err: {str(e)}")
        
        if "action" in data:
            session["game_active_tab_idx"] = 3
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"排名错误: {str(e)}")
        return jsonify({"status": "error", "msg": "排名更新操作失败"}), 400
        
@app.route('/api/save_ranking',methods=['POST'])     
def save_ranking():
    try:
        # 基础验证
        if 'game_id' not in session:
            return jsonify({
                "status": "error",
                "msg": "Missing game session",
                "code": "GAME_SESSION_EXPIRED"
            }), 400

        game_id = session['game_id']
        game_config = session.get("game_config", {})
        ranking_data = game_config.get("ranking", [])

        # 数据有效性验证
        if not isinstance(ranking_data, list) or len(ranking_data) == 0:
            return jsonify({
                "status": "error",
                "msg": "Invalid ranking data format",
                "code": "INVALID_RANKING_DATA"
            }), 400

        
        for idx, player_data in enumerate(ranking_data, start=1):
            required_fields = ["player_id", "net_score", "win_cnt", "loss_cnt"]
            if not all(field in player_data for field in required_fields):
                continue
            # 尝试查找现有记录
            existing = GameHistory.query.filter(
                and_(
                    GameHistory.game_id == session['game_id'],
                    GameHistory.player_id == player_data['player_id']
                )
            ).first()

            if existing:
                # 更新现有记录
                existing.net_score = player_data['net_score']
                existing.ranking = idx
                existing.win_cnt = player_data['win_cnt']
                existing.loss_cnt = player_data['loss_cnt']
            else:
                # 插入新记录
                history = GameHistory(
                    game_id=game_id,
                    player_id=player_data["player_id"],
                    net_score=player_data["net_score"],
                    ranking=idx,
                    win_cnt=player_data["win_cnt"],
                    loss_cnt=player_data["loss_cnt"]
                )
                db.session.add(history)
    
        db.session.commit()
        
        try:
            game = Games.query.filter_by(id=session['game_id']).first()
            game.status = GameStatus.DONE
            db.session.commit()
        except Exception as e:
            print(f"Game Status Update Err: {str(e)}")
        
        return jsonify({"status": "success",}), 200

    except KeyError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "msg": f"Missing required field: {str(e)}",
            "code": "MISSING_FIELD"
        }), 400

    except ValueError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "msg": str(e),
            "code": "INVALID_VALUE"
        }), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "msg": "Internal server error",
            "code": "INTERNAL_ERROR",
            "debug": str(e)  # 生产环境应移除 debug 信息
        }), 500
        
def double_matches_reloading(matches, game_config):
    for i in range(len(matches)):
        ats = []
        hts = []
        ht_re = list(db.session.query(PlayGames.player_id,PlayGames.updated_at).filter(PlayGames.game_id==session['game_id'],PlayGames.match_idx==str(i),PlayGames.team==TeamType.HOME_TEAM).all())
        at_re = list(db.session.query(PlayGames.player_id,PlayGames.updated_at).filter(PlayGames.game_id==session['game_id'],PlayGames.match_idx==str(i),PlayGames.team==TeamType.AWAY_TEAM).all())
        for p in ht_re:
            re = db.session.query(Users.id,Users.username,Users.avatar,Users.gender).filter(Users.id==str(p[0])).first()
            re = dict(re._asdict())
            re["gender"] = 1 if re["gender"] == Gender.MALE else 0
            hts.append(re)
        for p in at_re:
            re = db.session.query(Users.id,Users.username,Users.avatar,Users.gender).filter(Users.id==str(p[0])).first()
            re = dict(re._asdict())
            re["gender"] = 1 if re["gender"] == Gender.MALE else 0
            ats.append(re)
        game_config["games"].append(
            {
                "away_team": ats,
                "home_team": hts,
                "score": [db.session.query(PlayGames.score).filter(PlayGames.game_id==session['game_id'],PlayGames.match_idx==str(i),PlayGames.team==TeamType.HOME_TEAM).first()[0],
                            db.session.query(PlayGames.score).filter(PlayGames.game_id==session['game_id'],PlayGames.match_idx==str(i),PlayGames.team==TeamType.AWAY_TEAM).first()[0]],
                "updated_at":ht_re[0].updated_at
            }
        )
        if sum(game_config["games"][-1]["score"]) > 0:
            game_config["games_progress"][i] = 1        
    
# TODO 单打比赛预加载        
def single_matches_reloading(matches, game_config):
    pass

@app.route("/game/<int:game_id>")
@login_required
def game(game_id):
    print("game_id: ",game_id)
    session['game_id'] = game_id
    game = Games.query.filter_by(id=session['game_id']).first()
    if not game:
        abort(404, description="Game not found")
    
    admin = db.session.query(Users.username,Users.avatar,Users.id).filter(Users.id==game.creator_id).first()
    matches = PlayGames.query.filter(PlayGames.game_id==session['game_id']).group_by(PlayGames.match_idx).all()
    gameshowtitle = ""
    idx = int(game.game_type.split("-")[1]) - 1
    if game.game_type.split("-")[0] == "double":
        gameshowtitle = double_event_list[idx]["title"]
    if game.game_type.split("-")[0] == "single":
        gameshowtitle = single_event_list[idx]["title"]
    if game.game_type.split("-")[0] == "team":
        gameshowtitle = team_event_list[idx]["title"]
    
    game_config = {
        "admin": dict(admin._asdict()),
        "game_id": session['game_id'],
        "gametype": game.game_type,
        "gametime": game.timestamp,
        "gametitle": game.title,
        "gamerule": game.rule,
        "gameshowtitle": gameshowtitle,
        "member_list" : json.loads(game.signup_data),
        "gamestatus": game.status.value,
        "games":[],
        "ranking":[],
        "games_progress" : [0] * len(matches),
        "updated_at":game.updated_at
    }
    
    # if game.status == GameStatus.READY:
    if len(matches) == 0:
        game_config["ranking"] = []
        for m in game_config["member_list"]:
            if m=="": continue
            game_config["ranking"].append({
            "player_id": m["id"],
            "player_name": m["username"],
            "player_avatar": m["avatar"],
            "win_cnt": 0,
            "loss_cnt": 0,
            "net_score": 0,
        }) 
    else:
        if game.game_type.split("-")[0] == "double":
            double_matches_reloading(matches=matches, game_config=game_config) 
        if game.game_type.split("-")[0] == "single":
            single_matches_reloading(matches=matches, game_config=game_config)
            
        game_config["ranking"] = player_ranking(session['game_id'],game_config["member_list"])

    
    session["game_config"] = game_config
    game_info = app.jinja_env.get_template("macros.html").module.game_info
    game_score = app.jinja_env.get_template("macros.html").module.game_score
    game_rank = app.jinja_env.get_template("macros.html").module.game_rank
    tabmenu = [
        {
           'tabname': "game_info",
           'tabshowname': "报名信息",
           'tabcontent': game_info(session["game_config"], list(Users.query.all()))
        },
        {
           'tabname': "game_score",
           'tabshowname': "对局积分",
           'tabcontent': game_score(session["game_config"])
        },
        {
           'tabname': "game_rank",
           'tabshowname': "比赛成绩",
           'tabcontent': game_rank(session["game_config"])
        },
        
        ]
    
    return render_template("game.html", tabName = "game",tabmenu = tabmenu, game_id=game_id)

@app.route("/game_import",methods=['POST'])
@login_required
def game_import():
    try:  
        # 检查文件是否存在
        if 'game_file' not in request.files:
            return jsonify({"status": "error", "msg": "未选择文件"}), 400
            
        file = request.files['game_file']
        
        # 验证文件名
        if file.filename == '':
            return jsonify({"status": "error", "msg": "无效文件名"}), 400
        
        # 生成唯一文件名
        filename = Config.unique_filename(file.filename)
        
        # 确保上传目录存在
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER,'game'), exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(Config.UPLOAD_FOLDER, 'game' , filename)
        file.save(file_path)
        
        session['game_id'] = create_game_with_csv(
            file_path=file_path,
            creator_id=current_user.id,
        )
        return jsonify({"status": "success",}), 200
    except Exception as e:
        print(f"导入失败: {str(e)}")
        db.session.rollback()
        return jsonify({"status": "error", "msg": str(e)}), 400

@app.route("/gamelist")
@login_required
def gamelist():
    games = []
    for game in Games.query.order_by(desc(Games.id)).all():
        user = Users.query.filter_by(id=game.creator_id).first()
        game_type = ""
        idx = int(game.game_type.split("-")[1]) - 1
        if game.game_type.split("-")[0] == "double":
            game_type = double_event_list[idx]["title"]
        if game.game_type.split("-")[0] == "single":
            game_type = single_event_list[idx]["title"]
        if game.game_type.split("-")[0] == "team":
            game_type = team_event_list[idx]["title"]
        games.append({
            "game_id": game.id,
            "gametype":game_type,
            "gametime":game.timestamp,
            "admin_name": user.username,
            "admin_avatar": user.avatar,
            "status": game.status,
            "gametitle": game.title
        })
    
    if(len(games) == 0):
        session["game_id"] = -1
        session.pop('game_config', None)
    return render_template("gamelist.html",games=games)

@app.route("/personal_info")
@login_required
def personal_info():
    print(current_user)
    return render_template("personal_info.html",user = current_user)

@app.route('/history')
@login_required
# TODO history func
def history():
    latest_results = (
    db.session.query(PlayGames.result, PlayGames.net_score)
        .filter(PlayGames.player_id == current_user.id)
        .filter(PlayGames.result != None)
        .order_by(PlayGames.game_id.desc(), PlayGames.match_idx.desc())
        .limit(10)
        .all()
    )
    print(latest_results)
    # 提取结果为列表
    Top10Matches = [(1,r.net_score) if r.result.value == "win" else (0,r.net_score) for r in latest_results]
    return render_template("history.html", Top10Matches=Top10Matches)

@app.route('/test')
def test():
    return render_template("test.html")

@app.route('/game/<int:game_id>/date', methods=['GET', 'POST'])
def date(game_id):
    # 验证会话和权限
    if 'game_id' not in session or session['game_id'] != game_id:
        return jsonify({
            "status": "error",
            "msg": "无权访问此比赛",
            "code": "UNAUTHORIZED"
        }), 403
    
    # GET请求处理
    if request.method == 'GET':
        return render_template("date.html", game_id=game_id)
    
    # POST请求处理
    try:
        gamestatus = session["game_config"]["gamestatus"]
        
        if gamestatus == GameStatus.DONE.value:
            return jsonify({
                "status": "success",
                "msg": "比赛已结束不可修改",
                "code": "GAME_ENDED"
            }), 200
            
        if gamestatus == GameStatus.ING.value:
            return jsonify({
                "status": "success",
                "msg": "比赛进行中不可修改",
                "code": "GAME_IN_PROGRESS"
            }), 200
            
        # 正常情况返回重定向
        return jsonify({
            "status": "redirect",
            "url": url_for('date', game_id=game_id, _external=True)
        })
        
    except KeyError as e:
        return jsonify({
            "status": "error",
            "msg": "会话数据不完整",
            "code": "MISSING_DATA"
        }), 400
    
@app.route('/api/save_date_time',methods=['POST'])
def save_date_time():
    data = request.get_json()
    try:
        # 方法1：直接拼接本地时间（推荐）
        start_local = datetime.strptime(
            f"{data['date']} {data['start_time']}", 
            "%Y-%m-%d %H:%M"
        )
        end_local = datetime.strptime(
            f"{data['date']} {data['end_time']}", 
            "%Y-%m-%d %H:%M"
        )
        
        # 方法2：解析ISO格式（无时区）
        start_iso = datetime.fromisoformat(data['start_iso'])
        end_iso = datetime.fromisoformat(data['end_iso'])
        
        game = Games.query.filter_by(id=session["game_config"]["game_id"]).first()
        game.timestamp = start_local
        db.session.commit()

        session["game_config"]["gametime"] = start_local
        session.modified = True
        return jsonify({
            'status': 'success',
            'saved_data': {
                'date': data['date'],
                'start': data['start_time'],
                'end': data['end_time'],
                'utc_start': start_local.astimezone(pytz.utc).isoformat(),
                'utc_end': end_local.astimezone(pytz.utc).isoformat()
            }
        })
    except Exception as e:
        print(str(e))
        return jsonify({'status': 'error', 'msg': str(e)}), 400

@app.route('/api/save_game_title',methods=['POST'])
def save_game_title():
    data = request.get_json()
    try:
        game = Games.query.filter_by(id=session["game_config"]["game_id"]).first()
        game.title = data["content"]
        db.session.commit()
        session["game_config"]["gametitle"] = data["content"]
        session.modified = True
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'status': 'error', 'msg': str(e)}), 400
    
@app.route('/api/save_game_rule',methods=['POST'])
def save_game_rule():
    data = request.get_json()
    try:
        game = Games.query.filter_by(id=session["game_config"]["game_id"]).first()
        print(data["content"])
        game.rule = data["content"]
        db.session.commit()
        session["game_config"]["gamerule"] = data["content"]
        session.modified = True
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'status': 'error', 'msg': str(e)}), 400

@app.route('/api/change_username', methods=['POST'])
@login_required
def change_username():
    try:
        new_username = request.json.get('username')
        # 
        if new_username is None:
            return jsonify({'status': 'error'}), 400
        
        # 检查用户名是否已存在（伪代码）
        if Users.query.filter_by(username=new_username).first():
            return jsonify({"status": 'success', "msg": "用户名已存在"}), 400
        
        current_user.username = new_username
        db.session.commit()
        
        all_games = Games.query.all()
        for game in all_games:
            try:
                signup_data = json.loads(game.signup_data)
            except Exception:
                continue
            
            changed = False
            for member in signup_data:
                if isinstance(member, str): continue
                if member["id"] == current_user.id:
                    member["username"] = current_user.username
                    changed = True
                    break
                
            if changed:
                try: 
                    game.signup_data = json.dumps(signup_data)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": 'error', "msg": str(e)}), 400

@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        # 验证 CSRF
        # validate_csrf(request.headers.get('X-CSRF-Token'))
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        # 验证当前密码是否正确
        if not bcrypt.check_password_hash(current_user.password, current_password):
            print("当前密码不正确")
            return jsonify({"status": "error", "msg": "当前密码不正确"}), 401
        
        # 更新密码（伪代码）
        current_user.password = bcrypt.generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({"status": "success", "msg": "密码修改成功"})
        
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/api/change_avatar', methods=['POST'])
@login_required
def change_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': '未选择文件'}), 400
    
    try:
        file = request.files['avatar']
        # 文件验证和保存逻辑...
        filename = secure_filename(f"user_{current_user.id}.png")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename))
        
        current_user.avatar = filename
        db.session.commit()
        
        all_games = Games.query.all()
        for game in all_games:
            try:
                signup_data = json.loads(game.signup_data)
            except Exception as e:
                print(str(e))
                continue
            
            changed = False
            for member in signup_data:
                if isinstance(member, str): continue
                if member["id"] == current_user.id:
                    member["avatar"] = current_user.avatar
                    changed = True
                    break
                
            if changed:
                try: 
                    game.signup_data = json.dumps(signup_data)
                    db.session.commit()
                except Exception as e:
                    print(str(e))
                    db.session.rollback()
    except Exception as e:
        print(str(e))
        return jsonify({'status': 'error', 'msg': str(e)}), 500
    
    
    return jsonify({
        'status': 'success',
        'avatar_url': url_for('static', filename=f'uploads/avatars/{filename}')
    })

@app.route('/debug-session')
def debug_session():
    return render_template("debug_session.html",session = session)

@app.route('/database-check')
def database_check():
    gs = Games.query.all()
    pgs = PlayGames.query.all()
    users = Users.query.all()
    return render_template("database-check.html", playgames = list(pgs), games = list(gs),users=list(users))
