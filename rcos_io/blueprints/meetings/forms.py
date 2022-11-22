"""
This module contains forms for meeting data.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeLocalField, SelectField
from wtforms.validators import InputRequired


class MeetingForm(FlaskForm):
    """The base form for a meeting object."""

    name = StringField("Name", validators=[])
    type = SelectField("Type", validators=[InputRequired()])
    start_date_time = DateTimeLocalField(
        "Starts", format="%Y-%m-%dT%H:%M", validators=[InputRequired()]
    )
    end_date_time = DateTimeLocalField(
        "Ends", format="%Y-%m-%dT%H:%M", validators=[InputRequired()]
    )
    location = StringField("Location")
