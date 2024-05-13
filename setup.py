# -*- coding: utf-8 -*-

from setuptools import setup


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='http_request_recorder',
    version='0.2.2',
    description='A package to record an respond to http requests, primarily for use in black box testing.',
    long_description=readme,
    author='',
    author_email='',
    url='https://github.com/sipgate/http-request-recorder',
    license=license,
    packages=['http_request_recorder'],
    install_requires=[
        'aiohttp~=3.8.4',
    ],
    zip_safe=False
)