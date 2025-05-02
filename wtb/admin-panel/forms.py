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
    """Form for adding or editing server."""
    name = StringField('Server Name', validators=[Length(max=100)])
    endpoint = StringField('Endpoint', validators=[DataRequired(), Length(max=255)])
    port = IntegerField('Port', validators=[DataRequired(), NumberRange(min=1, max=65535)])
    address = StringField('Interface Address', validators=[DataRequired(), Length(max=100)])
    public_key = StringField('Public Key', validators=[DataRequired(), Length(max=255)])
    geolocation_id = SelectField('Geolocation', validators=[DataRequired()], coerce=int)
    max_peers = IntegerField('Max Peers', validators=[Optional(), NumberRange(min=1)])
    status = SelectField('Status', validators=[DataRequired()], choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ])
    api_key = StringField('API Key', validators=[Length(max=255)])
    api_url = StringField('API URL', validators=[Length(max=255)])

class GeolocationForm(FlaskForm):
    """Form for adding or editing geolocation."""
    code = StringField('Code', validators=[DataRequired(), Length(min=2, max=20)])
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    available = BooleanField('Available')
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])