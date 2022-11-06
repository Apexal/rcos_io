from mailjet_rest import Client

from rcos_io.settings import MAILJET_API_KEY, MAILJET_API_SECRET

mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version="v3.1")


def send_otp_email(email: str, otp: str):
    data = {
        "Messages": [
            {
                "From": {"Email": "rcos.management@gmail.com", "Name": "RCOS"},
                "To": [{"Email": email}],
                "Subject": f"Your RCOS I/O OTP is {otp}",
                "TextPart": f"Your one-time password to sign-in to RCOS I/O is {otp}",
                "HTMLPart": f" Your one-time password to sign-in to RCOS I/O is <h1>{otp}</h1>",
                "CustomID": "OTP",
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)
    print(result.json())
    return result
