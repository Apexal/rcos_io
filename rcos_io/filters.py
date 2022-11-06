"""
This module contains custom template filters that can be used
in any template thanks to `@bp.app_template_filter()`.

Template filters are just functions that have a value passed into
them and generally perform some transformation. For example,
`capitalize` is a built-in filter and is used like so in a template
to capitalize the string variable `name`: `{{ name|captitalize }}`

Filters can take extra arguments besides the value they are called on.
See the `format_datetime` filter below as an example.

See
- https://flask.palletsprojects.com/en/2.2.x/templating/#registering-filters
- https://uniwebsidad.com/libros/explore-flask/chapter-8/custom-filters
"""

from typing import Union
from datetime import datetime
from flask import Blueprint

bp = Blueprint("filters", __name__)


@bp.app_template_filter()
def format_datetime(value: Union[datetime, str], strftime_format: str = "medium"):
    """Formats a date (either string or actual date obj) in the desired format."""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    if strftime_format == "date":
        strftime_format = "%x"

    return datetime.strftime(value, strftime_format)
