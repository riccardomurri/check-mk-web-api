from distutils.core import setup

setup(
    name='check_mk_web_api',
    packages=['check_mk_web_api'],
    version='1.1',
    description='Library to talk to Check_Mk Web API',
    author='Max Brenner',
    author_email='xamrennerb@gmail.com',
    url='https://github.com/brennerm/check-mk-web-api',
    download_url='https://github.com/brennerm/check-mk-web-api/archive/1.1.tar.gz',
    install_requires=['six'],
    keywords=['check_mk', 'api', 'monitoring']
)