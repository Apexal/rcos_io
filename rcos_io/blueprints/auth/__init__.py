"""
This module contains the authentication blueprint, which stores
all auth related views and functionality.
"""
from datetime import date
import functools
import random
import string
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast
from requests import HTTPError

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
from graphql.error import GraphQLError
from gql.transport.exceptions import TransportQueryError
from rcos_io.services import github, discord, email, utils, database, settings

C = TypeVar("C", bound=Callable[..., Any])


bp = Blueprint("auth", __name__, template_folder="templates")


@bp.before_app_request
def load_logged_in_user():
    """
    Set global user variables
    - is_logged_in
    - user
    - semesters
    - semester
    for access in views and templates.

    You can access these in views OR in templates with `g.user`
    """

    user: Optional[Dict[str, Any]] = session.get("user")

    # Fetch and store semester in session if not there or if it's changed
    if "semesters" not in session or session["semester"]["end_date"] < str(
        date.today()
    ):
        session["semesters"] = database.get_semesters(g.db_client)
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
            enrollment = database.get_enrollment(
                g.db_client, g.user["id"], session["semester"]["id"]
            )
            if enrollment:
                session["is_faculty_advisor"] = enrollment["is_faculty_advisor"]
                session["is_coordinator_or_above"] = (
                    enrollment["is_coordinator"] or session["is_faculty_advisor"]
                )
                # TODO
                session["is_mentor_or_above"] = session["is_coordinator_or_above"]

        g.logged_in_user_nickname = discord.generate_nickname(user) or g.user["email"]


def login_required(view: C) -> C:
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
    def wrapped_view(**kwargs: Any):
        if g.user is None:
            flash("You must login to view that page!", "danger")
            return redirect(url_for("auth.login", redirect_to=request.path))

        return view(**kwargs)

    return cast(C, wrapped_view)


def verified_required(view: C) -> C:
    """Flask decorator to require that the logged in user is verified to access the view.

    ```
    # Example
    @app.route('/secret')
    @verified_required
    def secret():
        return 'Hello verified users!'
    ```
    """

    @login_required
    @functools.wraps(view)
    def wrapped_view(**kwargs: Any):
        if not g.user["is_verified"]:
            flash("You must verified to view that page!", "danger")
            return redirect("/")

        return view(**kwargs)

    return cast(C, wrapped_view)


def setup_required(view: C) -> C:
    """
    Flask decorator to require that the logged in user has
    - Discord
    - GitHub
    - a secondary email
    set.

    ```
    # Example
    @app.route('/secret')
    @setup_required
    def secret():
        return 'Hello fully setup users!'
    ```
    """

    @verified_required
    @functools.wraps(view)
    def wrapped_view(**kwargs: Any):
        # Check what is not on the user yet and compile a error message
        not_done: List[str] = []
        if not g.user["first_name"]:
            not_done.append("adding your first name")
        if not g.user["last_name"]:
            not_done.append("adding your last name")
        if not g.user["discord_user_id"]:
            not_done.append("linking your Discord")
        if not g.user["github_username"]:
            not_done.append("linking your GitHub")
        if not g.user["secondary_email"]:
            not_done.append("adding your secondary email")
        if not g.user["is_secondary_email_verified"]:
            not_done.append("verifying your secondary email")

        if len(not_done) > 0:
            flash(
                f"You must finish your profile by {', '.join(not_done)}"
                "before accessing that page!",
                "danger",
            )
            return redirect(url_for("auth.profile"))

        return view(**kwargs)

    return cast(C, wrapped_view)


def rpi_required(view: C) -> C:
    """Flask decorator to require that the logged in user is an RPI user to access the view.

    ```
    # Example
    @app.route('/secret')
    @rpi_required
    def students_only():
        return 'Hello student!'
    ```
    """

    @setup_required
    @functools.wraps(view)
    def wrapped_view(**kwargs: Any):
        if g.user is None or g.user["role"] != "rpi":
            flash(
                "You must be an RPI student, faculty, or alum to view that page!",
                "danger",
            )
            return redirect("/")

        return view(**kwargs)

    return cast(C, wrapped_view)


def mentor_or_above_required(view: C) -> C:
    """
    Flask decorator to require that the logged in user is either currently a
    - Mentor
    - Coordinator
    - Faculty Advisor
    to access the view.

    ```
    # Example
    @app.route('/secret')
    @rpi_required
    def students_only():
        return 'Hello student!'
    ```
    """

    @setup_required
    @functools.wraps(view)
    def wrapped_view(**kwargs: Any):
        if not session.get("is_mentor_or_above"):
            flash(
                "You must be a Mentor or above to view this page!",
                "danger",
            )
            return redirect("/")

        return view(**kwargs)

    return cast(C, wrapped_view)


def coordinator_or_above_required(view: C) -> C:
    """
    Flask decorator to require that the logged in user is either currently a
    - Mentor
    - Coordinator
    - Faculty Advisor
    to access the view.

    ```
    # Example
    @app.route('/secret')
    @rpi_required
    def students_only():
        return 'Hello student!'
    ```
    """

    @setup_required
    @functools.wraps(view)
    def wrapped_view(**kwargs: Any):
        if not session.get("is_coordinator_or_above"):
            flash(
                "You must be a Coordinator or above to view that page!",
                "danger",
            )
            return redirect("/")

        return view(**kwargs)

    return cast(C, wrapped_view)


@bp.route("/login", methods=("GET", "POST"))
def login():
    """
    Renders the email login form with email hints for either RPI or external users.
    Handles login form submissions by generating OTPs and emailing them.
    """
    if request.method == "GET":
        # Check if user tried to go to website that requires auth and was redirected to login
        if request.args.get("redirect_to"):
            # Store the page they wanted to get to in the session, to use after successful login
            session["redirect_to"] = request.args.get("redirect_to")

        # "role" could be "rpi" or "external" to determine what to show on login page
        return render_template("auth/login.html", role=request.args.get("role"))

    # Handle POST request form submission
    user_email = request.form["email"]
    session["user_email"] = user_email

    # Generate and store OTP
    otp = generate_otp()
    session["user_otp"] = otp

    # Try sending OTP via Discord direct message
    try:
        user = database.find_user_by_email(g.db_client, user_email)
        if user and user["discord_user_id"]:
            dm_channel = discord.create_user_dm_channel(user["discord_user_id"])
            discord.dm_user(
                dm_channel["id"],
                f"**{otp}** is your one-time password to complete your login.",
            )
    except HTTPError as error:
        current_app.logger.exception(error)

    # Send it to the user via email
    if settings.ENV == "production":
        email.send_otp_email(user_email, otp)

    current_app.logger.info(f"OTP generated and sent for {user_email}: {otp}")

    # Render OTP form for user to enter OTP
    return render_template("auth/otp.html", user_email=user_email, otp=otp)


@bp.route("/login/otp", methods=("POST",))
def submit_otp():
    """
    Finish the login process by checking that the submitted OTP matches the OTP sent to the user.

    On correct:
    - Sets `user` in the session
    - and flashes

    On incorrect:
    - resets session
    - redirects to login page
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
        return redirect(url_for("auth.login"))

    # Check that OTP matches and flash error and go back to login if wrong OTP
    if submitted_otp != user_otp:
        flash("Wrong one-time password!", "danger")
        return redirect(url_for("auth.login"))

    ### Correct OTP, time to login! ###

    # Find or create the user from the email entered
    session["user"], is_new_user = database.find_or_create_user_by_email(
        g.db_client, user_email, "rpi" if "@rpi.edu" in user_email else "external"
    )
    g.user = session["user"]

    # Go home OR to the desired path the user tried going to before login
    if redirect_to:
        return redirect(redirect_to)

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

    # Attempt to complete OAuth2 flow and result in access token
    # and user info (id, username, avatar, etc.)
    try:
        discord_user_tokens = discord.get_tokens(code)
        discord_access_token = discord_user_tokens["access_token"]
        discord_user_info = discord.get_user_info(discord_access_token)
    except HTTPError as error:
        current_app.logger.exception(error)
        flash("Yikes! Failed to link your Discord.", "danger")
        return redirect("/")

    # Extract and store Discord user id on user in database
    discord_user_id = discord_user_info["id"]

    try:
        update_logged_in_user({"discord_user_id": discord_user_id})
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Yikes! Failed to save your Discord link.", "danger")
        return redirect("/")

    flash_message = (
        "Linked Discord account "
        f"@{discord_user_info['username']}#{discord_user_info['discriminator']}"
    )

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
            except HTTPError as error:
                current_app.logger.exception(error)
    except HTTPError as error:
        current_app.logger.exception(error)
        flash("Failed to add you to the Discord server.", "warning")

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

    # Attempt to complete OAuth2 flow and result in access token and user info
    # (id, username, avatar, etc.)
    try:
        github_user_tokens = github.get_tokens(code)
        github_access_token = github_user_tokens["access_token"]
        github_user_info = github.get_user_info(github_access_token)
    except HTTPError as error:
        current_app.logger.exception(error)
        flash("Yikes! Failed to link your GitHub.", "danger")
        return redirect("/")

    # All we really care about is their GitHub username
    github_username = github_user_info["login"]

    # Attempt to store GitHub username on user
    try:
        update_logged_in_user({"github_username": github_username})
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
        flash("Yikes! Failed to save your GitHub link.", "danger")
        return redirect("/")

    flash(f"Linked GitHub account @{github_username}", "primary")

    return redirect(url_for("auth.profile"))


@bp.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    """Renders the profile form on GET request and updates it on POST."""

    if request.method == "GET":
        # Fetch Discord user profile if linked
        context: Dict[str, Any] = {}
        if g.user["discord_user_id"]:
            context["discord_user"] = discord.get_user(g.user["discord_user_id"])

        return render_template("auth/profile.html", **context)

    # HANDLE FORM SUBMISSION

    # Store in database
    updates: Dict[str, Union[str, int]] = {}

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

    # Attempt to apply updates in database.
    # This will fail if constraints fails like secondary email is reused
    try:
        update_logged_in_user(updates)
        flash("Updated your profile!", "success")
    except (GraphQLError, TransportQueryError) as error:
        current_app.logger.exception(error)
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
    session["user"] = database.update_user_by_id(g.db_client, g.user["id"], updates)
    g.user = session["user"]

    # Update Discord nickname
    if g.user["discord_user_id"]:
        new_nickname = discord.generate_nickname(g.user)
        if new_nickname:
            try:
                discord.set_member_nickname(
                    cast(str, g.user["discord_user_id"]), new_nickname
                )
            except HTTPError as error:
                current_app.logger.exception(error)


def generate_otp(length: int = DEFAULT_OTP_LENGTH) -> str:
    """Randomly generates an alphabetic one-time password of the specified length in all caps."""

    otp = ""
    for _ in range(length):
        otp += random.choice(string.ascii_uppercase)

    return otp
