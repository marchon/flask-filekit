# -*- coding: utf-8 -*-

# import os.path
# from flask import Flask, url_for

# TODO

import urllib2, os.path
from flaskext.uploads import IMAGES, UploadConfiguration
from flaskext.filekit import FileKit, Field, Processor, Resize

class AdvertKit(FileKit):
    thumbnail = Field(processors=[Resize(100, 75, crop=True)])

AdvertKit.uset._config = UploadConfiguration('/tmp/uploads')
fp = urllib2.urlopen('http://ss.solberg.is/315d46d41f.png')
image = AdvertKit.save(fp, filename='image.png')
assert os.path.exists(image.path)
assert not os.path.exists(image.thumbnail.path)
image.thumbnail.url # Call url to create file
assert os.path.exists(image.thumbnail.path)
assert image.thumbnail.path.endswith('.jpg')