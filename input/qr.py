#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-07-25

import sys
import cv2
from subprocess import Popen, PIPE, STDOUT
from gi.repository import GdkPixbuf
from input.visual import cv2_image_to_gdk_pixbuf, gdk_pixbuf_export, Input

def qr (image):
    pixbuf = cv2_image_to_gdk_pixbuf (image)
    data = gdk_pixbuf_export (pixbuf)
    
    p = Popen(['zbarimg', '-q', '--raw', 'JPG:-'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    stdout = p.communicate (input = data) [0]
    return stdout.strip ().decode ('utf8')


#if __name__ == '__main__':
def main ():
    image = cv2.imread (sys.argv [1])
    ocr = qr (image)
    print (ocr)

class QR:
    def __init__ (self, text):
        self.text = text
    
    def __str__ (self):
        return text

class QRInput (Input):
    def poll (self):
        image = None
        if self.ui.focus_on:
            image = self.ui.get_focus ('color')
        else:    
            image = self.ui.get_focus ('raw')

        text = qr (image)
        
        if len (text) > 0:
            return text
        else:
            return None
