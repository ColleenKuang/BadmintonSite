import os
from uuid import uuid4

basedir = os.path.abspath(os.path.dirname(__file__))
print(basedir)
class Config(object):
    # APP MODE
    DEBUG = False
    
    SESSION_TYPE = 'redis'
    
    # Top secret of website
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'A-VERL-LONG-SECRET-KEY'
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY') or 'A-VERL-LONG-SECRET-KEY'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    WTF_CSRF_CHECK_DEFAULT = False
    TEMPLATES_AUTO_RELOAD = True
    
    # 配置文件上传
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads/')
    # 头像设置
    ALLOWED_PIC_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB限制
    
    # 文件上传设置
    ALLOWED_PIC_EXTENSIONS = {'xls', 'xlsx', 'csv'}
    @staticmethod
    def allowed_pic_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_PIC_EXTENSIONS
               
    @staticmethod
    def allowed_games_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_GAME_EXTENSIONS

    @staticmethod
    def unique_filename(filename):
        ext = filename.rsplit('.', 1)[1].lower()
        return f"{uuid4().hex}.{ext}"