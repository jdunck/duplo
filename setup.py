from setuptools import setup

with open('README.rst', 'r') as fh:
    long_description = fh.read()

setup(
    name='duplo',
    version='1.0.1',
    description='Makes testing easier',
    long_description=long_description,
    author='Jeremy Dunck',
    author_email='jdunck@gmail.com',
    url='https://github.com/jdunck/duplo',
    packages=['duplo'],
    classifiers=[]
)