#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-08-06

import sys
import cv2, numpy as np
from input.color import get_mean_color_multi

class Colormap:
    proximity_tolerance = 10
    color_tolerance = 40

    def __len__ (self):
        return len (self.contour)
    
    def __init__ (self):
        self.mean_color = (0,0,0)
        self.contour = np.ndarray ((0, 1, 2), dtype = np.uint64)

        #if pixel is not None:
            #self.pixels = np.array ([[[pixel]]], dtype = np.uint32)
            #self.mean_color = pixel [0], pixel [1], pixel [2]
            #if coords is not None:
                #self.contour = np.array ([[[coords [0], coords [1]]]])
    
        #print (pixel, self.pixels.dtype)

    def append (self, coords):
        #print (self.pixels, self.pixels.shape)
        #assert isinstance (pixels, np.ndarray) and pixels.shape [2] == 3
        #self.pixels = np.append (self.pixels, [[[pixels]]], axis = 0)
        self.contour = np.resize (self.contour, (self.contour.shape [0] + 1, 1, 2))
        self.contour [-1] = coords
    
    def check_proximity (self, x, y):
        distance = cv2.pointPolygonTest (self.contour, (x, y), True)
        return self.proximity_tolerance > distance
    
    def check_color (self, image, bgr):
        if isinstance (bgr, np.ndarray) and bgr.shape [0] is 3:
            bgr = bgr [0], bgr [1], bgr [2]
        
        assert isinstance (bgr, tuple) and len (bgr) is 3
        p = image [self.contour [-1][0][1], self.contour [-1][0][0]]
        #print (p, self.contour [-1][0])
        prev = p [0], p[1], p[2]
        #print (prev, bgr)
        #print (type (bgr))
        
        c1 = abs (bgr [0] - prev [0]) #< self.color_tolerance
        c2 = abs (bgr [1] - prev [1]) #< self.color_tolerance
        c3 = abs (bgr [2] - prev [2]) #< self.color_tolerance
        
        if c1 < self.color_tolerance:
            c1 = True
        else:
            c1 = False
        if c2 < self.color_tolerance:
            c2 = True
        else:
            c2 = False
        if c3 < self.color_tolerance:
            c3 = True
        else:
            c3 = False
        #print ( type (c1 ))
        #sys.exit ()
        #print (c1, c2, c3)
        return c1 and c2 and c3
    
    def calculate_mean_color (self):
        self.mean_color = get_mean_color_multi (self.pixels)

    def get_contour (self):
        return self.contour
    
    def get_image (self):
        return self.pixels

    def __str__ (self):
        return str (len (self.contour)) + ' contours'
        

def build_colormaps (image):
    height, width, t = image.shape
    print (height, width)
    colormaps = []
    
    for y in range (height):
        for x in range (width):
            print (x, y)#, end = ' ')
            match_found = False
            if len (colormaps):
                for c in colormaps:
                    #print (c, len (colormaps), x, y)
                    if c.check_proximity (x, y) and c.check_color (image, image [y][x]):
                        #print ('append')
                        c.append ((x, y))
                        match_found = True
                        break

                if not match_found:
                    #print ('new')
                    colormap = Colormap ()
                    colormap.append ((x, y))
                    colormaps.append (colormap)
                
            else:
                colormap = Colormap ()
                colormap.append ((x, y))
                colormaps.append (colormap)
    
    cv2.namedWindow ('0')
    print (len (colormaps))
    colormaps.sort (key = len, reverse = True)
    for colormap in colormaps:
        print (colormap)
        image.fill (0)
        cv2.drawContours (image, colormap.contour, -1, (255,255,255), 2)
        cv2.imshow ('0', image)
        cv2.waitKey ()

if __name__ == '__main__':
    build_colormaps (sys.argv [1])
