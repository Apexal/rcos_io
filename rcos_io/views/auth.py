from datetime import date
import functools
import random
import string
from typing import Any, Dict, Optional, Union
from urllib.error import HTTPError

from rcos_io.services import github, db, discord
from rcos_io import settings, utils

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
    """Set global user variables `is_logged_in`, `user`, and `logged_in_user_nickname` for access in views and templates."""
    user: Optional[Dict[str, Any]] = session.get("user")

    # Fetch and store semester in session if not there or if it's changed
    if "semesters" not in session or session["semester"]["end_date"] < str(
        date.today()
    ):
        session["semesters"] = db.get_semesters(g.db_client)
        session["semester"] = utils.active_semester(session["semesters"])

    g.is_logged_in = user is not None
    if user is None:
        g.user = None
    else:
        g.user = user

        if (
            "is_mentor_or_above" not in session
            or "is_coordinator_or_above" not in session
            or "is_faculty_advisor" not in session
        ):
            enrollment = db.get_enrollment(g.db_client, g.user["id"], session["semester"]["id"])
            if enrollment:
                session["is_faculty_advisor"] = enrollment["is_faculty_advisor"]
                session["is_coordinator_or_above"] = (
                    enrollment["is_coordinator"] or session["is_faculty_advisor"]
                )
                # TODO
                session["is_mentor_or_above"] = False

        g.logged_in_user_nickname = discord.generate_nickname(user) or g.user["email"]


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


def setup_required(view):
    """Flask decorator to require that the logged in user is has Discord, GitHub, and a secondary email set.

    ```
    # Example
    @app.route('/secret')
    @setup_required
    def secret():
        return 'Hello fully setup users!'
    ```
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if (
            g.user is None
            or not g.user["discord_user_id"]
            or not g.user["github_username"]
            or not g.user["secondary_email"]
            or not g.user["is_secondary_email_verified"]
        ):
            flash("You must finish your profile first!", "danger")
            return redirect("/")

        return view(**kwargs)

    return wrapped_view


def rpi_required(view):
    """Flask decorator to require that the logged in user is an RPI user to access the view.

    ```
    # Example
    @app.route('/secret')
    @rpi_required
    def students_only():
        return 'Hello student!'
    ```
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user["role"] != "rpi":
            flash(
                "You must be an RPI student, faculty, or alum to view that page!",
                "danger",
            )
            return redirect("/")

        return view(**kwargs)

    return wrapped_view


def mentor_or_above_required(view):
    """Flask decorator to require that the logged in user is either currently a Mentor, Coordinator, or Faculty Advisor to access the view.

    ```
    # Example
    @app.route('/secret')
    @rpi_required
    def students_only():
        return 'Hello student!'
    ```
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("is_mentor_or_above"):
            flash(
                "You must be a Mentor or above to view this page!",
                "danger",
            )
            return redirect("/")

        return view(**kwargs)

    return wrapped_view


def coordinator_or_above_required(view):
    """Flask decorator to require that the logged in user is either currently a Mentor, Coordinator, or Faculty Advisor to access the view.

    ```
    # Example
    @app.route('/secret')
    @rpi_required
    def students_only():
        return 'Hello student!'
    ```
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("is_coordinator_or_above"):
            flash(
                "You must be a Coordinator or above to view that page!",
                "danger",
            )
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

        if settings.ENV == "production":
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
    user_otp: Optional[str] = session.pop("user_otp", None)
    user_email: Optional[str] = session.pop("user_email", None)
    redirect_to: Optional[str] = session.pop("redirect_to", None)

    session.clear()

    # This better be set! If it isn't something fishy is up so abort!
    if user_otp is None or user_email is None:
        flash("There was an error logging you in. Please try again later.", "danger")
        return

    # Check that OTP matches and flash error and go back to login if wrong OTP
    if submitted_otp != user_otp:
        flash("Wrong one-time password!", "danger")
        return redirect(url_for("auth.login"))

    ### Correct OTP, time to login! ###

    # Find or create the user from the email entered
    session["user"], is_new_user = db.find_or_create_user_by_email(
        g.db_client, user_email, "rpi" if "@rpi.edu" in user_email else "external"
    )
    g.user = session["user"]

    # Go home OR to the desired path the user tried going to before login
    if redirect_to:
        return redirect(redirect_to)
    else:
        return redirect(url_for("auth.profile" if is_new_user else "index"))


@bp.route("/logout")
def logout():
    """Logs out the user by clearing the session."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@bp.route("/discord")
@login_required
def discord_auth():
    """Redirects to Discord's OAuth2 auth flow for linking accounts."""
    return redirect(discord.DISCORD_AUTH_URL)


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
        discord_user_tokens = discord.get_tokens(code)
        discord_access_token = discord_user_tokens["access_token"]
        discord_user_info = discord.get_user_info(discord_access_token)
    except HTTPError as e:
        flash("Yikes! Failed to link your Discord.", "danger")
        current_app.logger.exception(e)
        return redirect("/")

    # Extract and store Discord user id on user in database
    discord_user_id = discord_user_info["id"]

    try:
        update_logged_in_user({"discord_user_id": discord_user_id})
    except Exception as e:
        flash("Yikes! Failed to save your Discord link.", "danger")
        current_app.logger.exception(e)
        return redirect("/")

    flash_message = f"Linked Discord account @{discord_user_info['username']}#{discord_user_info['discriminator']}"

    # Attempt to add them to the Discord server (will do nothing if already in the server)
    try:
        response = discord.add_user_to_server(discord_access_token, discord_user_id)
        # Was not previously in server and now was added
        if response.status_code == 201:
            flash_message += " and added you to the RCOS server!"

        # Set Discord nickname
        new_nickname = discord.generate_nickname(g.user)
        if new_nickname:
            try:
                discord.set_member_nickname(g.user["discord_user_id"], new_nickname)
            except Exception as e:
                current_app.logger.exception(e)
    except HTTPError as e:
        current_app.logger.exception(e)

    flash(flash_message, "primary")

    return redirect(url_for("auth.profile"))


@bp.route("/github")
def github_auth():
    """Redirect to GitHub's OAuth2 flow for linking accounts."""
    return redirect(github.GITHUB_AUTH_URL)


@bp.route("/github/callback")
def github_callback():
    """
    The callback URL that GitHub redirects to after getting user consent.

    This view:
    1. Exchanges GitHub OAuth2 code for access token
    """

    # Code comes from GitHub, meant to be exchanged for access tokens for the user
    code = request.args.get("code")
    if code is None:
        flash("What are you trying to do...", "danger")
        return redirect("/")

    # Attempt to complete OAuth2 flow and result in access token and user info (id, username, avatar, etc.)
    try:
        github_user_tokens = github.get_tokens(code)
        github_access_token = github_user_tokens["access_token"]
        github_user_info = github.get_user_info(github_access_token)
    except HTTPError as e:
        flash("Yikes! Failed to link your GitHub.", "danger")
        current_app.logger.exception(e)
        return redirect("/")

    # All we really care about is their GitHub username
    github_username = github_user_info["login"]

    # Attempt to store GitHub username on user
    try:
        update_logged_in_user({"github_username": github_username})
    except Exception as e:
        flash("Yikes! Failed to save your GitHub link.", "danger")
        current_app.logger.exception(e)
        return redirect("/")

    flash(f"Linked GitHub account @{github_username}", "primary")

    return redirect(url_for("auth.profile"))


@bp.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    """Renders the profile form on GET request and updates it on POST."""

    if request.method == "GET":
        # Fetch Discord user profile if linked
        context: Dict[str, Any] = dict()
        if g.user["discord_user_id"]:
            context["discord_user"] = discord.get_user(g.user["discord_user_id"])

        return render_template("auth/profile.html", **context)
    else:
        # Store in database
        updates: Dict[str, Union[str, int]] = dict()

        def handle_update(input_name: str):
            if (
                input_name in request.form
                and request.form[input_name].strip()
                and len(request.form[input_name].strip()) > 0
            ):
                updates[input_name] = request.form[input_name].strip()

        handle_update("first_name")
        handle_update("last_name")
        handle_update("graduation_year")
        handle_update("secondary_email")

        # If changing secondary email, mark it as unverified
        if "secondary_email" in updates:
            updates["is_secondary_email_verified"] = False

        # Attempt to apply updates in DB. This will fail if constraints fails like secondary email is reused
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
    session["user"] = db.update_user_by_id(g.db_client, g.user["id"], updates)
    g.user = session["user"]

    # Update Discord nickname
    if g.user["discord_user_id"]:
        new_nickname = discord.generate_nickname(g.user)
        if new_nickname:
            try:
                discord.set_member_nickname(g.user["discord_user_id"], new_nickname)
            except Exception as e:
                current_app.logger.exception(e)


def generate_otp(length: int = DEFAULT_OTP_LENGTH) -> str:
    """Randomly generates an alphabetic one-time password of the specified length in all caps."""

    otp = ""
    for _ in range(length):
        otp += random.choice(string.ascii_uppercase)

    return otp
