from setuptools import setup, find_packages

VERSION = '0.0.2'
DESCRIPTION = 'working with Android device via ADB'
LONG_DESCRIPTION = DESCRIPTION

setup(
    name='bugdroid',
    version=VERSION,
    author='shioko',
    author_email='ichisadashioko@gmail.com',
    url='https://github.com/ichisadashioko/bugdroid',
    license='GPLv3',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[],
    keywords=['python', 'android', 'adb'],
)
