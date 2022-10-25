import functools
import random
import string
from typing import Any, Dict
from urllib.error import HTTPError

from rcos_io.db import find_or_create_user_by_email, update_user_by_id
from rcos_io.settings import ENV
from ..discord import DISCORD_AUTH_URL, add_user_to_server, get_tokens, get_user_info, set_member_nickname, generate_nickname
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


bp = Blueprint("auth", __name__, url_prefix="/")


@bp.before_app_request
def load_logged_in_user():
    """Set global user variables `is_logged_in` and `user` for access in views and templates."""
    user: Dict[str, Any] | None = session.get("user")

    g.is_logged_in = user is not None
    if user is None:
        g.user = None
    else:
        g.user = user
        g.logged_in_user_nickname = generate_nickname(user) or g.user["email"]


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


def verified_required(view):
    """Flask decorator to require that the logged in user is verified to access the view.

    ```
    # Example
    @app.route('/secret')
    @verified_required
    def secret():
        return 'Hello verified users!'
    ```
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or not g.user["is_verified"]:
            flash("You must verified to view that page!", "danger")
            return redirect("/")

        return view(**kwargs)

    return wrapped_view


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "GET":
        # Check if user tried to go to website that requires auth and was redirected to login
        if request.args.get("redirect_to"):
            # Store the page they wanted to get to in the session, to use after successful login
            session["redirect_to"] = request.args.get("redirect_to")

        # "role" could be "rpi" or "external" to determine what to show on login page
        return render_template("auth/login.html", role=request.args.get("role"))
    elif request.method == "POST":
        user_email = request.form["email"]
        session["user_email"] = user_email

        # Generate and store OTP
        otp = generate_otp()
        session["user_otp"] = otp

        if ENV == "production":
            # Send it to the user via email
            # send_otp_to_email(user_email, otp)
            pass

        current_app.logger.info(f"OTP generated and sent for {user_email}: {otp}")

        # Render OTP form for user to enter OTP
        return render_template("auth/otp.html", user_email=user_email, otp=otp)


@bp.route("/login/otp", methods=("POST",))
def otp():
    """
    Finish the login process by checking that the submitted OTP matches the OTP sent to the user.

    Sets `user` in the session on success, and flashes, resets session, and redirects to login on fail.
    """

    # Grab the OTP from the submitted form
    submitted_otp = request.form["otp"]

    # Grab and then clear session variables
    user_otp: str | None = session.pop("user_otp", None)
    user_email: str | None = session.pop("user_email", None)
    redirect_to: str | None = session.pop("redirect_to", None)

    session.clear()

    if user_otp is None or user_email is None:
        flash("There was an error logging you in. Please try again later.", "danger")
        return

    # Check that OTP matches and flash error and go back to login if wrong OTP
    if submitted_otp != user_otp:
        flash("Wrong one-time password!", "danger")
        return redirect(url_for("auth.login"))

    # Correct OTP, time to login!

    # Find or create the user from the email entered
    session["user"] = find_or_create_user_by_email(
        user_email, "rpi" if "@rpi.edu" in user_email else "external"
    )
    g.user = session["user"]

    # Go home OR to the desired path the user tried going to before login
    if redirect_to:
        return redirect(redirect_to)
    else:
        return redirect(url_for("index"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@bp.route("/discord")
@login_required
def discord():
    """Redirects to Discord's auth flow for linking accounts."""
    return redirect(DISCORD_AUTH_URL)


@bp.route("/discord/callback")
@login_required
def discord_callback():
    """
    The callback URL that Discord redirects to after getting user consent.

    This view:
    1. Exchanges Discord OAuth2 code for access token
    2. Fetches Discord user info with the token
    3. Stores the Discord user id on the user database record.
    """

    code = request.args.get("code")
    if code is None:
        return redirect("/")

    # Attempt to complete OAuth2 flow and result in access token and user info (id, username, avatar, etc.)
    try:
        discord_user_tokens = get_tokens(code)
        discord_access_token = discord_user_tokens["access_token"]
        discord_user_info = get_user_info(discord_access_token)
    except HTTPError as e:
        flash("Yikes! Failed to link your Discord.", "danger")
        current_app.logger.exception(e)
        return redirect("/")

    # Extract and store Discord user id on user in database
    discord_user_id = discord_user_info["id"]

    try:
        session["user"] = update_user_by_id(
            g.user["id"], {"discord_user_id": discord_user_id}
        )
        g.user = session["user"]
    except Exception as e:
        flash("Yikes! Failed to save your Discord link.", "danger")
        current_app.logger.exception(e)
        return redirect("/")

    flash_message = f"Linked Discord account @{discord_user_info['username']}#{discord_user_info['discriminator']}"

    # Attempt to add them to the Discord server (will do nothing if already in the server)
    try:
        response = add_user_to_server(discord_access_token, discord_user_id)
        # Was not previously in server and now was added
        if response.status_code == 201:
            flash_message += " and added you to the RCOS server!"
        
        # Set Discord nickname
        new_nickname = generate_nickname(g.user)
        print(new_nickname)
        if new_nickname:
            try:
                set_member_nickname(g.user["discord_user_id"], new_nickname)
            except Exception as e:
                current_app.logger.exception(e)
    except HTTPError as e:
        current_app.logger.exception(e)

    flash(flash_message, "primary")

    return redirect("/")


@bp.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    """Renders the profile form on GET request and updates it on POST."""
    if request.method == "GET":
        return render_template("profile.html")
    else:
        # Store in database
        updates: Dict[str, str | int] = dict()
        if request.form["first_name"] and request.form["first_name"].strip():
            updates["first_name"] = request.form["first_name"].strip()
        
        if request.form["last_name"] and request.form["last_name"].strip():
            updates["last_name"] = request.form["last_name"].strip()

        if request.form["graduation_year"]:
            try:
                updates["graduation_year"] = int(request.form["graduation_year"])
            except ValueError:
                pass
        
        try:
            update_logged_in_user(updates)
            flash("Updated your profile!", "success")
        except Exception as e:
            current_app.logger.exception(e)
            flash("There was an error while updating your profile!", "danger")

        return redirect(url_for("auth.profile"))


##################################################################

DEFAULT_OTP_LENGTH = 4

def update_logged_in_user(updates: Dict[str, Any]):
    """
    Updates the logged in user.
    
    1. Applies DB update
    2. Updates `session['user']` and `g.user`
    3. Updates Discord nickname if linked
    """
    session["user"] = update_user_by_id(
        g.user["id"], updates
    )
    g.user = session["user"]

    # Update Discord nickname
    if g.user["discord_user_id"]:
        new_nickname = generate_nickname(g.user)
        if new_nickname:
            try:
                set_member_nickname(g.user["discord_user_id"], new_nickname)
            except Exception as e:
                current_app.logger.exception(e)

def generate_otp(length: int = DEFAULT_OTP_LENGTH) -> str:
    """Randomly generates an alphabetic one-time password for a user to be sent and login with."""

    otp = ""
    for _ in range(length):
        otp += random.choice(string.ascii_uppercase)

    return otp
