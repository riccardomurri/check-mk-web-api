import os

from fire import Fire

from . import WebApi


def _param(value: str, what: str, paramname: str, varname: str) -> str:
    if value:
        return value
    try:
        value = os.environ[varname]
    except KeyError:
        raise RuntimeError(
            "Need to set {what},"
            " either via command-line option `{paramname}=...`,"
            " or via environment variable `{varname}`."
            .format(**locals()))
    return value


class Cli(WebApi):
    """
    Command-line client for CheckMK web API.
    """
    def __init__(self,
                 url: str = None,
                 username: str = None,
                 secret: str = None):
        url = _param(url, "CheckMK API URL", "url", "CHECK_MK_URL")
        username = _param(username, "CheckMK automation user name", "username", "CHECK_MK_USER")
        secret = _param(secret, "CheckMK automation secret", "secret", "CHECK_MK_SECRET")
        super(Cli, self).__init__(url, username, secret)

Fire(Cli)
