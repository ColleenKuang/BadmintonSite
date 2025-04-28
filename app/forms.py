from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, FileField,PasswordField, SubmitField, BooleanField, RadioField
from wtforms.validators import DataRequired, Length

from app.models import Users

class RegisterForm(FlaskForm):
    username = StringField('Username',validators=[DataRequired(),Length(min=1,max=15)])
    password = PasswordField('Password',validators=[DataRequired(),Length(min=6,max=15)])
    gender = RadioField('Label', choices=[('1','男'),('2','女')])
    # confirm = PasswordField('Repeat Password',validators=[DataRequired(),Length(min=6,max=15)])
    # recaptcha = RecaptchaField()
    avatar = FileField('上传头像', validators=[DataRequired()])
    submit = SubmitField('注册')
    def validate_register(self):
        user = Users.query.filter_by(username = self.username.data).first()
        if user:
            return "Username already taken."
        # if self.username.data in list(db["User"]):
            
        
        # if self.password.data != self.confirm.data:
        #     return "The password must be same."
        
        return ""
    
    
class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    remember = BooleanField('记住我')
    login_btn = SubmitField('登录')
    register_btn = SubmitField('注册')