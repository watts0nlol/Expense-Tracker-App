from flask_login import current_user


def get_user_id():
    """
    Returns the current logged-in user's ID, or None if not logged in.
    """
    if current_user.is_authenticated:
        return current_user.userID
    return None