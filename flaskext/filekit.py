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
from flaskext.uploads import UploadSet, DEFAULTS


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
    
    def get_filename(self):
        """ Fields should respect the `ext` parameter and overwrite the source
        extension. This is usually governed by the last processor in this 
        field. """
        name, ext = self.fkit.filename.rsplit('.', 1)
        if self._field.extension():
            ext = self._field.extension()
        return '.'.join((name, ext))
    
    def save(self):
        """ Run a file pointer through all processors. Processors are 
        responsible for seek(0). """
        with open(self.fkit.path) as fp:
            for processor in self._field.processors:
                fp = processor(fp)
            self.fkit.uset.save(FileStorage(fp), folder=self.folder, name=self.get_filename())
        
    @property
    def path(self):
        return self.fkit.uset.path(os.path.join(self.folder, self.get_filename()))
        
    @property
    def url(self):
        """ If file does not yet exist we generate the file now. """
        if not os.path.exists(self.path):
            self.save()
        return self.fkit.uset.url(self.path)
        

class Field(object):
    """
    This represents the options for a field. 
    
    :param processors: A list of `filekit.Processor` instances that generate
                       the desired output. The first processor receives a file 
                       pointer to the source file. All processors should 
                       return a file pointer rewinded (`seek(0)`). The outcome
                       is persisted in the right location.
    :param ext: The extension to save and fetch the file with. If a source 
                file has a ``png`` extension and a field generates a ``jpg`` 
                thumbnail for it in a field, you must specify the final 
                extension in the field options for the file to be served with 
                the appropriate mimetype headers.
    :param pre_cache: With this boolean option set to True the file is 
                      generated at the same time the source file is persisted.
                      Otherwise file is processed with `url` of 
                      `filekit.BoundField` is accessed.
    """
    
    def __init__(self, processors, ext=None, pre_cache=False):
        self.processors = processors
        self.ext = ext
        self.pre_cache = pre_cache
    
    def extension(self):
        if self.ext is None and hasattr(self.processors[-1], 'ext'):
            return self.processors[-1].ext
        return self.ext


class FileKit(object):
    """
    Subclasses of `filekit.FileKit` act as specification for a certain type
    of file you with to handle the uploading and processing for. Do define
    which derivative files to process and persist use class attributes with
    `filekit.FileKit.Field` instances.
    
        from flaskext.filekit import FileKit, Field, Processor, Resize

        class ProfileImageKit(FileKit):
            thumbnail = Field(processors=[Resize(120, 120, crop=True)])

    :param filename: The filename label for the source file. Save this value
                     in some storage to retrieve the FileKit instance again.
    
    """
    __metaclass__ = DeclarativeFieldsMetaclass
    
    uset = UploadSet('files', DEFAULTS) # Overwrite
    
    def __init__(self, filename):
        self.filename = filename
        for folder, field in self.fields.items():
            setattr(self, folder, BoundField(folder, field, self))
    
    @classmethod
    def save(cls, storage, filename=None):
        """
        asdf
        
        :param storage: The uploaded file to save. `werkzeug.FileStorage` 
                        objects are prefered but other file pointers should
                        be fine.
        :param filename: The filename it will be saved under. Flask-Upload
                         may overwrite this value so use `FileKit.filename` of
                         this instance after calling `FileKit.save` to persist
                         the filename.
        
        """
        if not isinstance(storage, FileStorage):
            storage = FileStorage(storage, filename=filename)
            # , 'must file pointer or yield strings'
        filename = cls.uset.save(storage, name=filename)
        instance = cls(filename)
        instance.process(force=False)
        instance.filename = filename
        return instance
    
    def process(self, force=True):
        for field_label in self.fields:
            field = getattr(self, field_label)
            if field._field.pre_cache or force:
                field.save()
    
    @property
    def path(self):
        """
        Returns the absolute path to the persisted file. Does not check if 
        the file exists.
        """
        return self.uset.path(self.filename)
    
    @property
    def url(self):
        """
        Returns the URL for this file.
        """
        return self.uset.url(self.filename)


class Processor(object):
    """ Base processor class. Processors are simply callables that return file
    pointers. Overwrite `process` method. """

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
    Adopted from django-imagekit. Handles resizing of image files. Returns a 
    temporary file handler to a JPEG file. Fields ending with this processor 
    should specify a `jpg` extensions in the `ext` argument. This processor
    returns `tempfile.TemporaryFile` file pointer.
        
    :param width: The desired width of the resized image. Not guaranteed 
                  depending on values of `imagekit.Resize.crop` and 
                  `imagekit.Resize.upscale`.
    :param height: The desired height of the resized image. Not guaranteed 
                   depending on values of `imagekit.Resize.crop` and 
                   `imagekit.Resize.upscale`.
    :param crop: Wether to crop the image.
    :param upscale: Wether to respect desired dimensions even if source file 
                    is smaller.
    :param quality: The JPEG quality of the final image.

    """
    
    format = 'JPEG'
    ext = 'jpg'
    
    def __init__(self, width, height, crop=False, upscale=False, quality=80):
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

