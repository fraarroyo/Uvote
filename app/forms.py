from flask_wtf.file import FileField, FileAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

class CandidateForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    party_list = SelectField('Party List', coerce=int, validators=[DataRequired()])
    position_id = SelectField('Position', coerce=int, validators=[DataRequired()])
    college_id = SelectField('College', coerce=int, validators=[Optional()])
    image = FileField('Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class PositionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    election_id = SelectField('Election', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Submit') 