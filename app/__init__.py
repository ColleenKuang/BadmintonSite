from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate


from config import Config
from datetime import datetime
app = Flask(__name__)
app.config.from_object(Config)

cors = CORS(app)  # 允许所有域的跨域请求
bootstrap = Bootstrap5(app)
db = SQLAlchemy(app)
login = LoginManager(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
migrate = Migrate(app, db)
# login.init_app(app)
# 用于指定当未登录用户尝试访问受保护页面时，重定向到的登录页面路由。
login.login_view = 'login'
login.login_message = 'You must login to access this page'
login.login_message_category = 'info'

double_event_list = [
        {
            'id': "double-1",
            'title': '多人轮转赛',
            'description': '适合水平差距小',
            'image_url': '/static/images/event2.png',
            'avaliable': "True",
        },
        {
            'id': "double-2",
            'title': '固搭循环赛',
            'description': '适合固定搭档',
            'image_url': '/static/images/event2.png',
            'avaliable': "True",
        },
        {
            'id': "double-3",
            'title': 'A+B匹配赛',
            'description': '适合强带弱',
            'image_url': '/static/images/event2.png',
            'avaliable': "True",
        },
        {
            'id': "double-4",
            'title': '固搭擂台赛',
            'description': '组队挑战擂主',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
        {
            'id': "double-5",
            'title': '匹配擂台赛',
            'description': '配队友挑战擂主',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
        {
            'id': "double-6",
            'title': '单败淘汰赛',
            'description': '敬请期待',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
        {
            'id': "double-7",
            'title': '双败淘汰赛',
            'description': '敬请期待',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
        {
            'id': "double-8",
            'title': '血战到底',
            'description': '敬请期待',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
    ]

single_event_list = [
        {
            'id': "single-1",
            'title': '单打循环赛',
            'description': '适合固定搭档',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
        {
            'id': "single-2",
            'title': '单打擂台赛',
            'description': '组队挑战擂主',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
        {
            'id': "single-3",
            'title': '单打淘汰赛',
            'description': '适合强带弱',
            'image_url': '/static/images/no event.png',
            'avaliable': False
        },
]

team_event_list = [
    {
        'id': "team-1",
        'title': '团队对位赛',
        'description': '适合团队间PK',
        'image_url': '/static/images/no event.png',
        'avaliable': False
    },
    {
        'id': "team-2",
        'title': '五羽轮比',
        'description': '适合固定搭档',
        'image_url': '/static/images/no event.png',
        'avaliable': False
    },
    {
        'id': "team-3",
        'title': '团队固搭赛',
        'description': '适合固定搭档',
        'image_url': '/static/images/no event.png',
        'avaliable': False
    },
    {
        'id': "team-4",
        'title': '经典团队赛',
        'description': '适合队伍对抗',
        'image_url': '/static/images/no event.png',
        'avaliable': False
    },
]

from app.route import * 