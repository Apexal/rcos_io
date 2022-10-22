import functools
import random
import string
from flask import (
    current_app,
    Blueprint,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)


bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user():
    user_id: str | None = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = {"id": user_id}


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "GET":
        if request.args.get("redirect_to"):
            session["redirect_to"] = request.args.get("redirect_to")

        return render_template("auth/login.html")
    elif request.method == "POST":
        user_email = request.form["email"]
        session["user_email"] = user_email

        # Generate OTP
        otp = generate_otp()
        session["user_otp"] = otp

        if current_app.config.get('TESTING'):
            print("OTP:", otp)
        else:
            # Send it to the user via email
            # send_otp_to_email(user_email, otp)
            print("OTP:", otp) # TODO: remove
            pass

        # Render OTP form for user to enter OTP
        return render_template("auth/otp.html", user_email=user_email)


@bp.route("/login/otp", methods=("POST",))
def otp():
    """
    Finish the login process by checking that the submitted OTP matches the OTP sent to the user.

    Sets `user_id` in the session on success, and flashes, resets session, and redirects to login on fail.
    """

    # Grab the OTP from the submitted form
    submitted_otp = request.form["otp"]

    # Grab and then clear session variables
    user_otp: str | None = session.pop("user_otp", None)
    user_email: str | None = session.pop("user_email", None)
    redirect_to: str | None = session.pop("redirect_to", None)

    session.clear()

    # Check that OTP matches and flash error and go back to login if wrong OTP
    if submitted_otp != user_otp:
        flash("Wrong one-time password!", "danger")
        redirect(url_for("auth.login"))

    # Correct OTP, time to login!

    # Find or creat the user from the email entered
    # user = find_or_create_user_by_email(user_email)
    # session['user_id'] = user['id']
    session["user_id"] = "fakeid"

    # Go home OR to the desired path the user tried going to before login
    if redirect_to:
        return redirect(redirect_to)
    else:
        return redirect(url_for("index"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


##################################################################

DEFAULT_OTP_LENGTH = 8


def generate_otp(length: int = DEFAULT_OTP_LENGTH) -> str:
    """Randomly generates an alphabetic one-time password for a user to be sent and login with."""

    otp = ""
    for _ in range(length):
        otp += random.choice(string.ascii_uppercase)

    return otp


def login_required(view):
    """Flask decorator to require that the user is logged in to access the view.

    ```
    # Example
    @app.route('/secret')
    @login_required
    def secret():
        return 'Hello logged in users!'
    ```
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("You must login to view that page!", "danger")
            return redirect(url_for("auth.login", redirect_to=request.path))

        return view(**kwargs)

    return wrapped_view
