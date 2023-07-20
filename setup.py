# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='http_request_recorder',
    version='0.1.0',
    description='A package to record an respond to http requests, primarily for use in black box testing.',
    long_description=readme,
    author='',
    author_email='',
    url='https://github.com/sipgate-labs/http-request-recorder',
    license=license,
    packages=['http_request_recorder'],
    install_requires=[
        'aiohttp~=3.8.4',
    ],
    zip_safe=False
)