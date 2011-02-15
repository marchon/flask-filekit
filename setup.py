"""
Flask-Filekit
-------------
Handles processing of uploaded files. It uses Flask-Uploads to manage files 
but acts as a layer on top to handle declarations and processing of descendant 
files such as thumbnails. Resize processor included.

"""
from setuptools import setup


setup(
    name='Flask-Filekit',
    version='0.0.1',
    url='https://github.com/jokull/flask-filekit/',
    license='MIT',
    author='Jokull Solberg Audunsson',
    author_email='jokull@solberg.is',
    description='Upload and process files into descendant files',
    long_description=__doc__,
    packages=['flaskext'],
    namespace_packages=['flaskext'],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask>=0.5'
    ],
    tests_require='nose',
    test_suite='nose.collector',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
