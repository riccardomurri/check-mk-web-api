from setuptools import setup

setup(
    name='cmkclient',
    packages=['cmkclient'],
    version='1.6',
    description='A library and command-line client to talk to Check_Mk Web API',
    author='Max Brenner, Riccardo Murri',
    author_email='riccardo.murri@gmail.com',
    url='https://github.com/riccardomurri/cmkclient',
    download_url='https://github.com/riccardomurri/cmkclient/archive/1.4.tar.gz',
    install_requires=[
        'enum34;python_version<"3.4"',
        'fire',
        'six',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    keywords=['check_mk', 'api', 'monitoring']
)
