"""
This module contains constants and functions for interacting with the Discord API.
"""

from typing import Any, Dict, Optional, TypedDict, Union, cast
from typing_extensions import NotRequired
import requests
from rcos_io.services import settings

DISCORD_VERSION_NUMBER = "10"
DISCORD_API_ENDPOINT = f"https://discord.com/api/v{DISCORD_VERSION_NUMBER}"


# See https://discord.com/developers/docs/topics/oauth2#authorization-code-grant
DISCORD_AUTH_URL = (
    "https://discord.com/api/oauth2/authorize"
    f"?client_id={settings.DISCORD_CLIENT_ID}&redirect_uri={settings.DISCORD_REDIRECT_URL}"
    "&response_type=code&scope=identify%20guilds.join&prompt=none"
)

HEADERS = {
    "Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}",
}
"""
Base headers to send along with Discord API requests.

Most important is the `Authorization` header with the Discord bot's secret token
which authenticates requests and gives us permission to do things as the bot.
"""


class DiscordTokens(TypedDict):
    """
    https://discord.com/developers/docs/topics/oauth2#authorization-code-grant-access-token-response
    """

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str


def get_tokens(code: str) -> DiscordTokens:
    """
    Given an authorization code
    - requests the access and refresh tokens for a Discord user

    See
    https://discord.com/developers/docs/topics/oauth2#authorization-code-grant-access-token-exchange-example

    Args:
        code: the authorization code returned from Discord
    Returns:
        a DiscordTokens dict containing access token, expiration, etc.
    Raises:
        HTTPError: if HTTP request fails
    """
    response = requests.post(
        f"{DISCORD_API_ENDPOINT}/oauth2/token",
        data={
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.DISCORD_REDIRECT_URL,
            "scope": "identity guilds.join",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    tokens = response.json()
    return tokens


class DiscordUser(TypedDict):
    """See https://discord.com/developers/docs/resources/user#user-object"""

    id: str
    username: str
    discriminator: str
    avatar: NotRequired[str]
    banner: NotRequired[str]
    accent_color: NotRequired[str]


def get_user_info(access_token: str) -> DiscordUser:
    """
    Given an access token get a Discord user's info including
    - id
    - username
    - discriminator
    - avatar url
    - etc.

    Args:
        access_token: Discord access token for a user
    Raises:
        HTTPError on request failure

    See:
    https://discord.com/developers/docs/topics/oauth2#authorization-code-grant-access-token-exchange-example
    """
    response = requests.get(
        f"{DISCORD_API_ENDPOINT}/users/@me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    user = response.json()
    return user


def add_user_to_server(access_token: str, user_id: str):
    """
    Given a Discord user's id, add them to the RCOS server with the given nickname.

    Args:
        access_token: Discord user's access token
        user_id: Discord user's account ID
    Raises:
        HTTPError on failed request

    See https://discord.com/developers/docs/resources/guild#add-guild-member
    """
    data = {
        "access_token": access_token,
    }
    response = requests.put(
        f"{DISCORD_API_ENDPOINT}/guilds/{settings.DISCORD_SERVER_ID}/members/{user_id}",
        json=data,
        headers=HEADERS,
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    return response


def get_user(user_id: str) -> Union[DiscordUser, None]:
    """
    Given a Discord user's id, gets their user info.

    Args:
        user_id: Discord user's unique account ID
    Returns:
        DiscordUser
    Raises:
        HTTPError on failed request (e.g. not found)

    See https://discord.com/developers/docs/resources/user#get-user
    """
    response = requests.get(
        f"{DISCORD_API_ENDPOINT}/users/{user_id}", headers=HEADERS, timeout=3
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    user = response.json()
    return user


def create_user_dm_channel(user_id: str):
    """
    https://discord.com/developers/docs/resources/user#create-dm
    """
    response = requests.post(
        f"{DISCORD_API_ENDPOINT}/users/@me/channels",
        json={
            "recipient_id": user_id,
        },
        headers=HEADERS,
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    return cast(Dict[str, Any], response.json())


def dm_user(dm_channel_id: str, message_content: str):
    """
    https://discord.com/developers/docs/resources/channel#create-message
    """
    response = requests.post(
        f"{DISCORD_API_ENDPOINT}/channels/{dm_channel_id}/messages",
        json={"content": message_content},
        headers=HEADERS,
        timeout=3,
    )
    response.raise_for_status()
    return response.json()


def add_role_to_member(user_id: str, role_id: str):
    """
    Adds a role to a server member.

    Args:
        user_id: Discord user's unique account ID (same as member ID)
        role_id: ID of Discord role to add to member
    Raises:
        HTTPError on failed request (will not fail if role is already set)

    See https://discord.com/developers/docs/resources/guild#modify-guild-member
    """
    response = requests.put(
        f"{DISCORD_API_ENDPOINT}/guilds/{settings.DISCORD_SERVER_ID}"
        f"/members/{user_id}/roles/{role_id}",
        headers=HEADERS,
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    return response


def kick_user_from_server(user_id: str):
    """
    Given a Discord user's id, kicks them from the RCOS server.

    Args:
        user_id: Discord user's unique account ID
    Raises:
        HTTPError on failed request (e.g. missing permission to kick member)

    See https://discord.com/developers/docs/resources/guild#remove-guild-member
    """
    response = requests.delete(
        f"{DISCORD_API_ENDPOINT}/guilds/{settings.DISCORD_SERVER_ID}/members/{user_id}",
        headers=HEADERS,
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    return response


def set_member_nickname(user_id: str, nickname: str):
    """
    Given a Discord user's id, sets their nickname on the server.

    Args:
        user_id: Discord user's unique account ID
        nickname: the nickname to give the user, must be <= 32 characters
    Raises:
        HTTPError on failed request

    See https://discord.com/developers/docs/resources/guild#modify-current-member
    """
    response = requests.patch(
        f"{DISCORD_API_ENDPOINT}/guilds/{settings.DISCORD_SERVER_ID}/members/{user_id}",
        json={"nick": nickname},
        headers=HEADERS,
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    return response


def generate_nickname(user: Dict[str, Any]) -> Optional[str]:
    """
    Bill Ni, graduating 2022, nib@rpi.edu -> Bill N '22 (nib)
    Glen Darling, IBM, glendarling@us.ibm.com -> Glen D
    """

    name = ""
    if user["first_name"] and user["last_name"]:
        name = f"{user['first_name']} {user['last_name'][0]}"
    elif user["first_name"]:
        name = user["first_name"]
    elif user["rcs_id"]:
        return user["rcs_id"]

    nickname = name
    if user["graduation_year"]:
        nickname += f" '{str(user['graduation_year'])[2:4]}"

    if user["rcs_id"]:
        nickname += f" ({user['rcs_id']})"

    return nickname
