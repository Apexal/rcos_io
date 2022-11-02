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
