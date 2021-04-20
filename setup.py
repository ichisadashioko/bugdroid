from setuptools import setup, find_packages

VERSION = '0.0.1'
DESCRIPTION = 'working with Android device via ADB'
LONG_DESCRIPTION = DESCRIPTION

setup(
    name='bugdroid',
    version=VERSION,
    author='shioko',
    author_email='<ichisadashioko@gmail.com>',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[],
    keywords=['python', 'android', 'adb'],
)
