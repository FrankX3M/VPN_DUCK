# Add this code to forms.py
# This should be the entire content of the file

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, BooleanField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Optional, Length

class ServerForm(FlaskForm):
    """Form for adding and editing servers"""
    name = StringField('Server Name')
    endpoint = StringField('Endpoint', validators=[DataRequired()])
    port = IntegerField('Port', validators=[DataRequired(), NumberRange(min=1, max=65535)], default=51820)
    address = StringField('Internal IP', validators=[DataRequired()])
    public_key = StringField('Public Key', validators=[DataRequired()])
    geolocation_id = SelectField('Geolocation', validators=[DataRequired()], coerce=int)
    max_peers = IntegerField('Maximum Peers', default=100, validators=[Optional()])
    api_key = StringField('API Key')
    api_url = StringField('API URL')
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('degraded', 'Degraded')
    ], default='active')

class GeolocationForm(FlaskForm):
    """Form for adding and editing geolocations"""
    code = StringField('Country Code', validators=[DataRequired(), Length(min=2, max=3)])
    name = StringField('Name', validators=[DataRequired()])
    available = BooleanField('Available', default=True)
    description = StringField('Description')

class FilterForm(FlaskForm):
    """Form for filtering server list"""
    search = StringField('Search')
    geolocation = SelectField('Geolocation', choices=[], coerce=str, default='all')
    status = SelectField('Status', choices=[
        ('all', 'All Statuses'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('degraded', 'Degraded')
    ], default='all')