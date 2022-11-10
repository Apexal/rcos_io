"""
This module contains all GitHub related functionality.
"""
from typing import TypedDict, Optional
import datetime
import requests
from rcos_io.services import settings

GITHUB_API_URL = "https://api.github.com"
GITHUB_AUTH_URL = (
    "https://github.com/login/oauth/authorize"
    f"?client_id={settings.GITHUB_APP_CLIENT_ID}&redirect_uri={settings.GITHUB_APP_REDIRECT_URL}"
)


class GitHubTokens(TypedDict):
    """
    https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps#response
    """

    access_token: str
    scope: str
    token_type: int


def get_tokens(code: str) -> GitHubTokens:
    """
    Given an authorization code, request an access token for a GitHub user.

    Returns:
        GitHubTokens
    Raises:
        HTTPError on failed request

    See https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
    """
    response = requests.post(
        "https://github.com//login/oauth/access_token",
        data={
            "client_id": settings.GITHUB_APP_CLIENT_ID,
            "client_secret": settings.GITHUB_APP_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_APP_REDIRECT_URL,
        },
        headers={"Accept": "application/json"},
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    tokens = response.json()
    return tokens


class User(TypedDict):
    """
    https://docs.github.com/en/rest/users/users#get-the-authenticated-user
    """

    id: str
    login: str
    avatar_url: str  # link to github profile page


def get_user_info(access_token: str) -> User:
    """
    Given an access token, get a GitHub user's info including id, username (login), avatar_url, etc.
    Throws an error on failed request.

    See https://docs.github.com/en/rest/users/users#get-the-authenticated-user
    """
    response = requests.get(
        f"{GITHUB_API_URL}/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.github+json",
        },
        timeout=3,
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    user = response.json()
    return user


class Person(TypedDict):
    """Subset of object used in GitHub API responses."""

    name: str
    email: str
    date: str


class Commit(TypedDict):
    """Subset of commit object in GitHub API responses."""

    url: str
    author: Person
    committer: Person
    message: str
    comment_count: int


class CommitInfo(TypedDict):
    """Subset of top-level commit info object in GitHub API responses."""

    url: str
    sha: str
    html_url: str
    comments_url: str
    commit: Commit
    author: User
    committer: User


#    html url structure: https://github.com/Apexal/rcos_io
#     api url structure: https://api.github.com/repos/Apexal/rcos_io

#          get branches: https://api.github.com/repos/Apexal/rcos_io/branches
#           get commits: https://api.github.com/repos/Apexal/rcos_io/commits
#   get commits by user: ?author=username or email
#     get commits since: ?since=ISO-8601 timestamp <-- starttime
#     get commits until: ?until=ISO-8601 timestamp <-- endtime
# get commits from head: ?sha=commit sha


def gen_params(**kwargs):
    """
    Generates params for request querystring.
    """
    valid_keys = {"author", "since", "until", "sha"}
    params = {"per_page": 100}  # get 100 commits per page
    for arg_key, arg_val in kwargs.items():
        # only include valid github api parameters
        # only include non None values
        if arg_key in valid_keys and arg_val is not None:
            params[arg_key] = arg_val
    return params


def get_commits(
    repolink: str,
    starttime: datetime.datetime,
    endtime: datetime.datetime = datetime.datetime.now(),
    user: Optional[str] = None,
):
    """
    Grabs all commits on all branches for a given GitHub repo, after a given time.

    takes >
         repolink: github html url
        starttime: datetime object for when to grab commits since
          endtime: datetime object for when to grab commits until
             user: username for desired user to filter commits for

    returns >
        all_commits: dictionary of commits >
            key: commit -> tree -> sha
            value: dictionary of commit info >
                key: "url"
                value: html url of commit
                ;
                key: "timestamp"
                value: ISO-8601 timestamp of commit
    """

    # convert datetime objects to iso strings
    starttime, endtime = starttime.isoformat(), endtime.isoformat()

    # grabs "owner_username/repo_name"
    repoid = repolink[repolink.index("github.com/") + len("github.com/") :]

    if repoid[-1] == "/":  # remove trailing slash
        repoid = repoid[:-1]

    # grabs branches for repo (limited to 100 branches due to pagination)
    # do not add branch pagination for now due to repos not having >100 branches
    raw_branches = requests.get(
        f"{GITHUB_API_URL}/repos/{repoid}/branches", timeout=3
    ).json()
    # grab commit links for branch heads
    branch_heads = [branch["commit"]["url"] for branch in raw_branches]

    all_commits = {}

    for head in branch_heads:
        # grabs "sha" from branch head url
        head_sha = head[head.index("commits/") + len("commits/") :]
        # grabs commits starting from branch head
        commit_list = requests.get(
            f"{GITHUB_API_URL}/repos/{repoid}/commits",
            params=gen_params(
                sha=head_sha, author=user, since=starttime, until=endtime
            ),
            timeout=3,
        ).json()

        # repeatedly grab commit pages while github api returns 100 commits (max)
        while len(commit_list) == 100:
            break_outer = False
            for commit in commit_list:
                # get tree sha (!= github api sha)
                # (this will exclude commits that are repeated e.g. merge commits)
                tree_sha = commit["commit"]["tree"]["sha"]
                if (
                    tree_sha in all_commits
                ):  # found commit upstream, stop fetching commits
                    break_outer = True
                    break
                # add commit to returned dictionary
                # attach html url and timestamp as values
                all_commits[tree_sha] = {
                    "url": commit["html_url"],
                    "timestamp": commit["commit"]["author"]["date"],
                }
            if break_outer:
                break

            # last commit on request page
            last_sha = commit_list[-1]["sha"]

            # repeat request with last commit
            commit_list = requests.get(
                f"{GITHUB_API_URL}/repos/{repoid}/commits",
                params=gen_params(
                    sha=last_sha, author=user, since=starttime, until=endtime
                ),
                timeout=3,
            ).json()

    return all_commits
