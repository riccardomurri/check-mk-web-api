"""
Module that contains the command line app.
"""
# Why does this file exist, and why not put this in __main__?
#
#   You might be tempted to import things from __main__ later, but that will cause
#   problems: the code will get executed twice:
#
#   - When you run `python -mcmkclient` python will execute
#     ``__main__.py`` as a script. That means there won't be any
#     ``cmkclient.__main__`` in ``sys.modules``.
#   - When you import __main__ it will get executed again (as a module) because
#     there's no ``cmkclient.__main__`` in ``sys.modules``.
#
#   Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration

import os

from . import WebApi

from fire import Fire


__all__ = ['Cli', 'main']


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
    Command-line client for the CheckMK web API.

    Commands and their arguments are named exactly as the in the `command
    reference for the ChecMK HTTP-API, see:
    https://checkmk.com/cms_web_api_references.html

    Options ``--url``, ``--username``, and ``--secret`` are required in each
    invocation to provide the CheckMK endpoint and authentication values; if
    omitted, the corresponding values will be taken from environment variables
    ``CHECK_MK_URL``, ``CHECK_MK_USER`` and ``CHECK_MK_SECRET`` (respectively).
    """
    def __init__(self,
                 url: str = None,
                 username: str = None,
                 secret: str = None):
        url = _param(url, "CheckMK API URL", "url", "CHECK_MK_URL")
        username = _param(username, "CheckMK automation user name", "username", "CHECK_MK_USER")
        secret = _param(secret, "CheckMK automation secret", "secret", "CHECK_MK_SECRET")
        super(Cli, self).__init__(url, username, secret)


def main():
    """
    Run a CheckMK web API call from the command-line.

    Uses the `Fire`__ module to turn command-line arguments into a method call
    on the `Cli`:class: object.  Help text is also taken from that class'
    docstrings.

    .. __: https://github.com/google/python-fire/blob/master/docs/guide.md
    """
    # there is no documented way of passing a command-line arguments to
    # `Fire()`, so this `main()` methods takes no arguments and just lets
    # `Fire()` consume `sys.argv`.
    Fire(Cli)
