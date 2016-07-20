#!/usr/bin/python
from setuptools import setup

setup(name='cmdpack',
	version='0.1.0',
	description='command call back filter package',
	url='http://github.com/jeppeter/cmdpack',
	author='jeppeter Wang',
	author_email='jeppeter@gmail.com',
	license='MIT',
	packages=['cmdpack'],
	install_requires=[
		'tempfile',
		'unittest'
	],
	keyword = ['commandline'],
	zip_safe=False)