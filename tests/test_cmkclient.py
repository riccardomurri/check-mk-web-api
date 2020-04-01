"""
Smoke tests for the command-line client.
"""

import sys

from cmkclient.cli import main


def test_main():
    # there is no documented way of passing a command-line arguments to
    # `Fire()`, so we need to temporarily change `sys.argv`
    saved_argv = sys.argv[:]
    try:
        sys.argv = ['cmkclient', '--help']
        main()
    except SystemExit as ex:
        assert ex.code == 0
    finally:
        sys.argv = saved_argv
