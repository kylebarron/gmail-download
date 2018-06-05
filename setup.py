#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

requirements = [
    'google-api-python-client >= 1.7.3',
    'httplib2 >= 0.11.3',
    'oauth2client >= 4.1.2',
    'pandas >= 0.23.0',
    'python-dateutil >= 2.7.3',
]

setup_requirements = [
    'setuptools >= 38.6.0',
    'twine >= 1.11.0'
]

test_requirements = []

setup(
    author="Kyle Barron",
    author_email='barronk@mit.edu',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    description="Download emails from Gmail",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='gmail_download',
    name='gmail_download',
    packages=find_packages(include=['gmail_download']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/kylebarron/gmail_download',
    version='0.0.1',
    zip_safe=False,
)
