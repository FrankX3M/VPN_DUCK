from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange

class LoginForm(FlaskForm):
    """Login form for user authentication."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class FilterForm(FlaskForm):
    """Filter form for server listing."""
    search = StringField('Search')
    geolocation = SelectField('Geolocation', choices=[('all', 'All Geolocations')])
    status = SelectField('Status', choices=[
        ('all', 'All Statuses'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('degraded', 'Degraded')
    ])
    view = SelectField('View Mode', choices=[
        ('table', 'Table View'),
        ('cards', 'Card View'),
        ('map', 'Map View')
    ])

class ServerForm(FlaskForm):
    """Form для добавления или редактирования сервера."""
    name = StringField('Название сервера', validators=[Length(max=100)])
    endpoint = StringField('Эндпоинт', validators=[DataRequired(), Length(max=255)])
    port = IntegerField('Порт', validators=[DataRequired(), NumberRange(min=1, max=65535)])
    address = StringField('Адрес интерфейса', validators=[DataRequired(), Length(max=100)])
    public_key = StringField('Публичный ключ', validators=[DataRequired(), Length(max=255)])
    geolocation_id = SelectField('Геолокация', validators=[DataRequired()], coerce=int)
    max_peers = IntegerField('Макс. клиентов', validators=[Optional(), NumberRange(min=1)])
    status = SelectField('Статус', validators=[DataRequired()], choices=[
        ('active', 'Активен'),
        ('inactive', 'Неактивен')
    ])
    api_key = StringField('API ключ', validators=[Length(max=255)])
    api_url = StringField('API URL', validators=[Length(max=255)])
    api_path = StringField('API путь', default='/status', validators=[Length(max=255)])
    skip_api_check = BooleanField('Пропустить проверку API', default=False)

class GeolocationForm(FlaskForm):
    """Form for adding or editing geolocation."""
    code = StringField('Code', validators=[DataRequired(), Length(min=2, max=20)])
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    available = BooleanField('Available')
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])