"""
This module contains GQL framents to use in other module's DB calls.
"""

BASIC_USER_DATA_FRAGMENT_INLINE = """
fragment basicUser on users {
  id
  is_verified
  first_name
  last_name
  display_name
  graduation_year
  preferred_name
  role
  email
  secondary_email
  is_secondary_email_verified
  rcs_id
  discord_user_id
  github_username
}
"""
