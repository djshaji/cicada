#!/usr/bin/env python3
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-07-02

from filters import Filter
import cv2

class Colorize (Filter):
    Color = 0
    name = "Colorize"
    
    def getopts (self):
        return [[int, "Color", 0, 11, 1, 0]]
        
    def filter (self, image):
        return cv2.applyColorMap (image, self.Color)
