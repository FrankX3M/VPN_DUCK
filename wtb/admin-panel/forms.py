from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, URL, NumberRange

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class FilterForm(FlaskForm):
    """Form for filtering servers and other data."""
    search = StringField('Search')
    geolocation = SelectField('Geolocation', choices=[('all', 'All Geolocations')])
    status = SelectField('Status', choices=[
        ('all', 'All Statuses'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('degraded', 'Degraded')
    ])

class ServerForm(FlaskForm):
    """Form for adding/editing server information."""
    name = StringField('Server Name', validators=[Length(max=100)])
    endpoint = StringField('Endpoint', validators=[DataRequired(), Length(max=255)])
    port = IntegerField('Port', default=51820, validators=[
        DataRequired(),
        NumberRange(min=1, max=65535)
    ])
    address = StringField('Address', validators=[Length(max=45)])
    public_key = StringField('Public Key', validators=[DataRequired(), Length(max=255)])
    geolocation_id = SelectField('Geolocation', coerce=int, validators=[DataRequired()])
    api_key = StringField('API Key', validators=[Length(max=100)])
    max_peers = IntegerField('Max Peers', default=100, validators=[
        Optional(),
        NumberRange(min=1, max=10000)
    ])
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('degraded', 'Degraded')
    ], validators=[DataRequired()])
    api_url = StringField('API URL', validators=[Optional(), URL(), Length(max=255)])

class GeolocationForm(FlaskForm):
    """Form for adding/editing geolocations."""
    code = StringField('Code', validators=[
        DataRequired(),
        Length(min=2, max=10)
    ])
    name = StringField('Name', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    available = BooleanField('Available', default=True)
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])