
from setuptools import setup

setup(
    name='bootstrap-linux',
    py_modules=['install'],
    description='Wrapper to install default apps on Linux enviroments',
    license='GNU GPLv3',
    author='Elmeri Niemela',
    version='1.0',
    include_package_data=True,
    install_requires=[],
    entry_points={'console_scripts': ['bootstrap-linux = install:main',],},
)
