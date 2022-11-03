"""
This module contains custom template filters that can be used in any template thanks to `@app.template_filter()`.

Template filters are just functions that have a value passed into them and generally perform some transformation.
For example, `capitalize` is a built-in filter and is used like so in a template to capitalize the string variable `name`:
`{{ name|captitalize }}`

Filters can take extra arguments besides the value they are called on. See the `format_datetime` filter below as an example.

See
- https://flask.palletsprojects.com/en/2.2.x/templating/#registering-filters
- https://uniwebsidad.com/libros/explore-flask/chapter-8/custom-filters
"""

from typing import Union
from datetime import date, datetime
from rcos_io import app


@app.template_filter()
def format_datetime(value: Union[datetime, str], format: str = "medium"):
    if type(value) == str:
        try:
            value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    if format == "date":
        format = "%x"

    return datetime.strftime(value, format)
