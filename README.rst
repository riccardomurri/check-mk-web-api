========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |requires|
        | |coveralls| |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/cmkclient/badge/?style=flat
    :target: https://readthedocs.org/projects/cmkclient
    :alt: Documentation Status

.. |travis| image:: https://api.travis-ci.org/riccardomurri/cmkclient.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/riccardomurri/cmkclient

.. |requires| image:: https://requires.io/github/riccardomurri/cmkclient/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/riccardomurri/cmkclient/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/riccardomurri/cmkclient/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/riccardomurri/cmkclient

.. |codecov| image:: https://codecov.io/gh/riccardomurri/cmkclient/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/riccardomurri/cmkclient

.. |version| image:: https://img.shields.io/pypi/v/cmkclient.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/cmkclient

.. |wheel| image:: https://img.shields.io/pypi/wheel/cmkclient.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/cmkclient

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/cmkclient.svg
    :alt: Supported versions
    :target: https://pypi.org/project/cmkclient

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/cmkclient.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/cmkclient

.. |commits-since| image:: https://img.shields.io/github/commits-since/riccardomurri/cmkclient/v1.6.0.svg
    :alt: Commits since latest release
    :target: https://github.com/riccardomurri/cmkclient/compare/v1.6.0...master



.. end-badges

A command-line client and Python3 library for using CheckMK web API.

* Free software: MIT license
* Supported Checkmk versions:
  - 1.6.0
  - 1.5.0


Installation
============

With ``pip``::

    pip install cmkclient

You can also install the in-development version with::

    pip install https://github.com/riccardomurri/cmkclient/archive/master.zip

You can also install from source code (for development)::

  git clone https://github.com/riccardomurri/cmkclient
  cd cmkclient
  sudo python setup.py install


Documentation
=============

Full documentation is available at:
`cmkclient.readthedocs.io <https://cmkclient.readthedocs.io/>`_

In general, methods and their arguments in the ``WebApi`` object are named
exactly as the in the `command reference for the HTTP-API
<https://checkmk.com/cms_web_api_references.html>`_.

Usage examples
--------------

All the Python examples assume a ``WebApi`` object has been created and bound
to variable ``api`` as in the following *Initialization* section.

Initialization
~~~~~~~~~~~~~~

Before using any of the CMKClient functionality in a Python program, you need
to create a ``WebApi`` object::

  import cmkclient
  api = cmkclient.WebApi('http://checkmk.example.org/check_mk/webapi.py', username='automation', secret='123456')

No such explicit initialization is needed when using the command-line client:
the web API is initialized automatically every time the CLI program is
started.

Add Host
~~~~~~~~

::

  >>> api.add_host('host.example.org')

Add Host in an existing WATO folder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  >>> api.add_host('host.example.org', folder='webservers')

Note there is no leading ``/`` on the folder name.

Edit Host
~~~~~~~~~

::

  >>> api.edit_host('host.example.org', ipaddress='192.168.0.100')

Delete Host
~~~~~~~~~~~

::

  >>> api.delete_host('host.example.org')

Get Host
~~~~~~~~

::

  >>> api.get_host('host.example.org')
  {
      'hostname': 'host.example.org',
      'attributes': {
          'ipaddress': '192.168.0.100'
      },
      'path': ''
  }

Get All Hosts
~~~~~~~~~~~~~

::

  >>> api.get_all_hosts()
  {
      'host.example.org': {
          'hostname': 'host.example.org',
          'attributes': {
              'ipaddress': '192.168.0.100'
          },
          'path': ''
      },
      'webserver01.com': {
          'hostname': 'webserver01.com',
          'attributes': {
              'ipaddress': '192.168.0.101'
          },
          'path': ''
      }
  }

Discover Services
~~~~~~~~~~~~~~~~~

::

  >>> api.discover_services('host.example.org')
  {'removed': '0', 'new_count': '16', 'added': '16', 'kept': '0'}

Bake Agents
~~~~~~~~~~~

::

  >>> api.bake_agents()

Activate Changes
~~~~~~~~~~~~~~~~

::

  >>> api.activate_changes()


Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
