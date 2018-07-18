#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-07-24

import sys
import cv2
from subprocess import Popen, PIPE, STDOUT
from gi.repository import GdkPixbuf
from input.visual import cv2_image_to_gdk_pixbuf, gdk_pixbuf_export, Input

def tesseract (image):
    pixbuf = cv2_image_to_gdk_pixbuf (image)
    data = gdk_pixbuf_export (pixbuf)
    
    # psm 7 is single line, psm 8 is word
    # to do: make it more automatic
    # autodetect various psm modes
    # try 7 then 8 then full page and so on
    p = Popen(['tesseract', '-psm', '7', 'stdin', 'stdout'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    stdout = p.communicate (input = data) [0]
    return stdout.strip ().decode ('utf8')

#if __name__ == '__main__':
def main ():
    image = cv2.imread (sys.argv [1])
    ocr = tesseract (image)

class OCR:
    def __init__ (self, text):
        self.text = text
    
    def __str__ (self):
        return text

class OCRInput (Input):
    def poll (self):
        image = None
        if self.ui.focus_on:
            image = self.ui.get_focus ('color')
        else:    
            image = self.ui.get_focus ('raw')
            
        ocr = tesseract (image)
        #self.ui.peep (image)
        if len (ocr) > 0:
            return ocr
        else:
            return None
