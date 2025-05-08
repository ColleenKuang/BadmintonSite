import os
from uuid import uuid4

basedir = os.path.abspath(os.path.dirname(__file__))
print(basedir)
class Config(object):
    # APP MODE
    DEBUG = True
    
    SESSION_TYPE = 'redis'
    
    # Top secret of website
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'A-VERY-LONG-SECRET-KEY'
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY') or 'A-VERY-LONG-SECRET-KEY'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_CHECK_DEFAULT = False
    TEMPLATES_AUTO_RELOAD = True
    
    # 文件夹配置
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads/')
    AVATAR_FOLDER = os.path.join(UPLOAD_FOLDER,'avatars')
    
    # 头像设置
    ALLOWED_PIC_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB限制
    
    # 文件上传设置
    ALLOWED_GAME_EXTENSIONS = {'xls', 'xlsx', 'csv'}
    @staticmethod
    def allowed_pic_file(filename):
        print(filename.rsplit('.', 1)[1].lower())
        print(filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_PIC_EXTENSIONS)
        print('.' in filename)
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