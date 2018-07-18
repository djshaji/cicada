#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-23

from gi.repository import GdkPixbuf
from enum import Enum
import input.color as color
from input.input import Input
import numpy as np
import cv2
import sys, os
from copy import deepcopy
from colour import Color
from warnings import warn

def gdk_pixbuf_scale (pixbuf, new_width, new_height):
    width = pixbuf.get_width ()
    height = pixbuf.get_height ()
    ratio = 1
    resized_width = 0
    resized_height = 0
    
    if width > height:
        ratio = width / height
        if new_width < new_height:
            resized_width = new_width
            resized_height = new_width / ratio
        else:
            resized_height = new_height
            resized_width = resized_height * ratio
    else:
        ratio = height / width
        if new_height > new_width:
            resized_width = new_width
            resized_height = new_width / ratio
        else:
            resized_height = new_height
            resized_width = resized_height * ratio

    return pixbuf.scale_simple (resized_width, resized_height, 2)


def resize (image, width, height, keep_aspect = True):
    if keep_aspect:
        w = image.shape [1]
        h = image.shape [0]
        
        aspect = w / h
        if w > h:
            height = int (width / aspect)
        elif h > w:
            width = int (height / aspect)
        elif h == w:
            height = width
        else:
            # demons in the program
            # run
            os.abort ()
    return cv2.resize (image, (width, height))

def cv2_image_to_gdk_pixbuf (image):
    if image is None:
        return None
    
    try:
        retval, jpg = cv2.imencode (".jpg", image)
    except Exception as e:
        print (e)
        return None
    
    loader = GdkPixbuf.PixbufLoader.new_with_type ("jpeg")
    loader.write (jpg)
    loader.close ()
    pixbuf = loader.get_pixbuf ()
    return pixbuf

def gdk_pixbuf_export (pixbuf, export_format = 'jpeg'):
    retval, data = pixbuf.save_to_bufferv (export_format, [None], [None])
    return data

class VideoInput:
    device = None
    width = 640
    height = 480
    resize = True
    
    def seek (self, frames):
        # alert!
        #we use seconds here now!
        pos = self.device.get (cv2.CAP_PROP_POS_MSEC)
        #print (pos)
        self.device.set (cv2.CAP_PROP_POS_MSEC, pos + (frames * 1000))
        
        return
        # aye!
        for x in range (frames):
            self.device.grab ()

    def __init__ (self, ui):
        self.ui = ui
        self.open = self.__open__
      
    def __open__ (self, device = 0):
        try:
            if self.device is None:
                self.device = cv2.VideoCapture (device)
            elif not self.device.isOpened ():
                self.device = cv2.VideoCapture (device)
            else:
                self.ui.message ("input device already initialized!", "input-error")
                return False
        except Exception  as e:
            self.ui.message ("input device cannot be opened!\n" + str (e), "input-error")
            return False

        self.ui.message ("input device opened", "input")
        return True
    
    def get_frame (self, raw = False):
        if raw:
            warn (str (NotImplemented))
        if self.device is not None and not self.device.isOpened ():
            self.ui.message ("input device not initialized!", "input-error")
            return
        
        retval, image = self.device.read ()
        
        if self.resize:
            return resize (image, self.width, self.height)
        else:
            return image
    
    def get_pixbuf (self):
        return cv2_image_to_gdk_pixbuf (self.get_frame ())
    
    def close (self):
        if self.device.isOpened ():
            self.device.release ()
        
        self.ui.message ("input device closed", "input")


class Camera (VideoInput):
    open = lambda self, device = 0: self.__open__ (device)

class Video (VideoInput):
    def open (self, filename):
        if not os.path.exists (filename):
            self.ui.message ("File not found: {}".format (filename), "input-error")
            return False
        
        return self.__open__ (device = filename)

class Picture (VideoInput):
    image = None
    filename = None

    def __open__ (self, filename):
        if isinstance (filename, np.ndarray):
            self.image = deepcopy (filename)
        else:
            self.filename = filename
            self.image = cv2.imread (filename)
        return self.get_frame ()
    
    def get_frame (self, raw = False):
        if raw:
            return self.image
        else:
            if self.resize:
                return resize (deepcopy (self.image), self.width, self.height)
            else:
                return deepcopy (self.image)
            #return deepcopy (self.image)
        #return self.__open__ (self.filename)
        
    def get_pixbuf (self):
        return cv2_image_to_gdk_pixbuf (self.get_frame ())

    def close (self):
        pass

class ColorFocus:
    radius = 20
    sidex = 50
    sidey = 50
    center = [50,50]
    color = (0,0,255)
    thickness = 2
    
    def __populate__ (self):
        contour = np.ndarray ((((self.sidex + self.sidey) *4), 1, 2), np.int32)
        contour .fill (0)
        #for x in range (self.center [0] - self.radius, self.center [0] + self.radius):
            #for y in range (self.center [1] - self.radius, self.center [1] + self.radius):
                #contour.append ((x,y))
        #print (self.center, self.sidex, self.sidey)
        counter = 0
        for x in (self.center [0] - self.sidex, self.center [0] + self.sidex):
            for y in range (self.center [1] - self.sidey, self.center [1] + self.sidey):
                contour [counter] = [x,y]
                counter += 1
        #counter = 0
        for y in (self.center [1] - self.sidey, self.center [1] + self.sidey):
            for x in range (self.center [0] - self.sidex, self.center [0] + self.sidex):
                contour [counter] = [x,y]
                counter += 1

        return contour
    
    def draw (self, image, center = -1, radius = -1):
        if center == -1:
            center = self.center
        if radius == -1:
            radius = self.radius
            
        #return cv2.rectangle (image, self.center [0] - self.side, self.center [1] + self.side, (255,255,255))

        return cv2.drawContours (image, self.__populate__ (), -1, self.color, self.thickness)
        #return cv2.polylines (image, self.__populate__ (), True, self.color, self.thickness)
        #return cv2.circle (image, center, radius, self.color, self.thickness)

    def get (self, image, raw = False):
        if raw:
            return self.__populate__ ()
        
        if image is None:
            #self.ui.message ("focus.get (): None passed as image!")
            return None

        # rare case scenario
        # putting it here but do think about it
        # if input image is less than selection side
        
        #side = self.side
        if image.shape [0] < self.sidex * 2 or image.shape [1] < self.sidey * 2:
            self.sidex = int ((image.shape [0] / 2) - 5)
            self.sidey = int ((image.shape [1] / 2) - 5)
            #if image.shape [0] > image.shape [1]:
                #self.side = int ((image.shape [0] / 2) - 5)
            #else:
                #self.side = int ((image.shape [1] / 2) - 5)
        
        if self.center [1] > image.shape [0] - (self.sidey + 2):
            #print (self.center, image.shape)
            self.center [1] = int (image.shape [0] - self.sidey - 2)

        if self.center [0] > image.shape [1]  - (self.sidex + 2):
            #print (self.center, image.shape)
            self.center [0] = int (image.shape [1] - self.sidex - 2)
        #print (self.center, image.shape)
        
        selection = np.ndarray (((self.sidey *2), (self.sidex * 2), 3), np.int32)
        xounter = self.center [0] - self.sidex
        younter = self.center [1] - self.sidey
        
        for y in range (self.center [1] - self.sidey, self.center [1] + self.sidey):
            for x in range (self.center [0] - self.sidex, self.center [0] + self.sidex):
                selection [y - younter, x - xounter] = image [y, x]

        return selection
                
class ColorInput (Input):
    def __init__ (self, ui):
        self.ui = ui
    
    def poll (self):
        image = self.ui.get_focus ()
        if image is None or not isinstance (image, np.ndarray):
            #self.ui.message ("ui.get_focus () returned None!", "input")
            return None
        
        #return color.get_mean_color_multi (image)
        c = color.get_mean_color_multi (image)
        tt = (c [2] / 255, c[1] / 255, c[0] / 255)
        c = Color (rgb = tt)
        return c
        #return c.get_hex_l ()

    def get_preview (self, color, size = -1):
        if size == -1:
            size = self.ui.PREVIEW_ICON_SIZE
        
        im = np.ndarray ((size, size, 3))
        c = Color (color)
        im [:] = (c.blue * 255, c.green * 255, c.red * 255)
        return im
        #pixbuf = cv2_image_to_gdk_pixbuf (im)
        #return pixbuf

def gdk_color_to_cv2 (color):
    return color.blue, color.green, color.red

if __name__ == '__main__':
    filename = sys.argv [1]
    im = cv2.imread (filename, -1)
    canny = cv2.Canny (im,200,200) # make this adjustable too
    i, cn, hr = cv2.findContours (canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    print (cn [0][0])
