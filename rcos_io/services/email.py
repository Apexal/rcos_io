"""
This module contains email-related functionality.
"""

from mailjet_rest import Client

from rcos_io.services import settings

mailjet = Client(
    auth=(settings.MAILJET_API_KEY, settings.MAILJET_API_SECRET), version="v3.1"
)


def send_otp_email(email: str, otp: str):
    """Send a one-time password to a particular email."""
    data = {
        "Messages": [
            {
                "From": {"Email": "rcos.management@gmail.com", "Name": "RCOS"},
                "To": [{"Email": email}],
                "Subject": f"Your RCOS I/O OTP is {otp}",
                "TextPart": f"Your one-time password to sign-in to RCOS I/O is {otp}",
                "HTMLPart": (
                    f" Your one-time password to sign-in to RCOS I/O is <h1>{otp}</h1>"
                ),
                "CustomID": "OTP",
            }
        ]
    }
    result = mailjet.send.create(data=data)
    return result
