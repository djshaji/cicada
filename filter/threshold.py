#!/usr/bin/env python3
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-07-03

from filters import Filter
import cv2

class AdaptiveThreshold (Filter):
    Threshold = 0
    Size = 3
    Method = 0
    name = "Adaptive Threshold"
    
    def getopts (self):
        return [[int, "Threshold", 0, 1, 1, 0],\
                [int, "Method",0, 1, 1, 0],\
                [int, "Size",3, 11, 2, 3]]
        
    def filter (self, image):
        #print (self.Size)
        return cv2.adaptiveThreshold (cv2.cvtColor (image, cv2.COLOR_BGR2GRAY), 1, self.Method, self.Threshold, self.Size, 1)
