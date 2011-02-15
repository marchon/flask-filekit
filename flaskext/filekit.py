# -*- coding: utf-8 -*-
"""
flaskext.filekit
================
This module makes it easier to declare files and their derivative versions 
(like images and thumbnails). Uses Flask-Uploads for uploading.

:copyright: 2010 Jökull Sólberg Auðunsson
:license:   MIT/X11, see LICENSE for details
"""

import os.path
from werkzeug import FileStorage
from flaskext.uploads import UploadSet


class DeclarativeFieldsMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = {}
        for field_name, obj in attrs.items():
            if isinstance(obj, Field):
                attrs['fields'][field_name] = attrs.pop(field_name)
        new_class = super(DeclarativeFieldsMetaclass,
                     cls).__new__(cls, name, bases, attrs)
        return new_class


class BoundField(object):
    
    def __init__(self, folder, field, fkit):
        self.folder = folder
        self._field = field
        self.fkit = fkit
    
    def save(self):
        with open(self.fkit.path) as fp:
            for processor in self._field.processors:
                fp = processor(fp)
            self.fkit.uset.save(FileStorage(fp), folder=self.folder, name=self.fkit.filename)
        
    @property
    def path(self):
        return self.fkit.uset.path(os.path.join(self.folder, self.fkit.filename))
        
    @property
    def url(self):
        if not os.path.exists(self.path):
            self.save()
        return self.fkit.uset.url(self.path)
        

class Field(object):
    
    def __init__(self, pre_cache, processors):
        self.pre_cache = pre_cache
        self.processors = processors


class FileKit(object):
    __metaclass__ = DeclarativeFieldsMetaclass
    
    uset = UploadSet('files', DEFAULTS) # Overwrite
    
    def __init__(self, filename):
        self.filename = filename
        for folder, field in self.fields.items():
            setattr(self, folder, BoundField(folder, field, self))
    
    def __contains__(self, name):
        return os.path.exists(self.uset.path(name))
    
    @classmethod
    def save(cls, storage, filename=None):
        if not isinstance(storage, FileStorage):
            storage = FileStorage(storage)
            # , 'must file pointer or yield strings'
        filename = cls.uset.save(storage, name=filename)
        instance = cls(filename)
        instance.process(cached=False)
        return instance
    
    def process(self, cached=True):
        for field_label in self.fields:
            field = getattr(self, field_label)
            if field._field.pre_cache:
                field.save()
    
    @property
    def path(self):
        return self.uset.path(self.filename)
    
    @property
    def url(self):
        return self.uset.url(self.filename)

class Processor(object):
    """ Base processor class """

    def process(self, fp):
        return fp

    def __call__(self, fp):
        fp = self.process(fp)
        fp.seek(0)
        return fp


import Image, ImageFile
ImageFile.MAXBLOCK = 1000000 # default is 64k
import tempfile

class Resize(Processor):
    """
    Adopted from django-imagekit.
    
    """
    
    format = 'JPEG'
    
    def __init__(self, width, height, crop=False, upscale=False, quality=95):
        self.width = width
        self.height = height
        self.crop = crop
        self.upscale = upscale
        self.quality = quality
    
    def img_to_fobj(self, img, fp):
        tmp = tempfile.TemporaryFile()
        img.save(tmp, self.format, quality=int(self.quality), optimize=True)
        return tmp
    
    def process(self, fp):
        img = Image.open(fp)
        cur_width, cur_height = img.size
        if self.crop:
            crop_horz = 1
            crop_vert = 1
            ratio = max(float(self.width)/cur_width, float(self.height)/cur_height)
            resize_x, resize_y = ((cur_width * ratio), (cur_height * ratio))
            crop_x, crop_y = (abs(self.width - resize_x), abs(self.height - resize_y))
            x_diff, y_diff = (int(crop_x / 2), int(crop_y / 2))
            box_left, box_right = {
                0: (0, self.width),
                1: (int(x_diff), int(x_diff + self.width)),
                2: (int(crop_x), int(resize_x)),
            }[crop_horz]
            box_upper, box_lower = {
                0: (0, self.height),
                1: (int(y_diff), int(y_diff + self.height)),
                2: (int(crop_y), int(resize_y)),
            }[crop_vert]
            box = (box_left, box_upper, box_right, box_lower)
            img = img.resize((int(resize_x), int(resize_y)), Image.ANTIALIAS).crop(box)
        else:
            if not self.width is None and not self.height is None:
                ratio = min(float(self.width)/cur_width,
                            float(self.height)/cur_height)
            else:
                if self.width is None:
                    ratio = float(self.height)/cur_height
                else:
                    ratio = float(self.width)/cur_width
            new_dimensions = (int(round(cur_width*ratio)),
                              int(round(cur_height*ratio)))
            if new_dimensions[0] > cur_width or \
               new_dimensions[1] > cur_height:
                if not self.upscale:
                    return self.img_to_fobj(img, fp)
            img = img.resize(new_dimensions, Image.ANTIALIAS)
        imgfile = self.img_to_fobj(img, fp)    
        return imgfile

