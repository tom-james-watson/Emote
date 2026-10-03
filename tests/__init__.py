from contextlib import ExitStack
from unittest.mock import patch


def isolate_user_data(directory):
    stack = ExitStack()
    stack.enter_context(patch("emote.user_data.SHELVE_PATH", directory + "/user_data"))
    stack.enter_context(
        patch("emote.user_data.SETTINGS_PATH", directory + "/Emote/settings.json")
    )
    return stack
