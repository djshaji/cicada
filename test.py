#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-07-22

import sys, cv2, numpy as np
from input.contour import contour_to_dispersion_hash, build_sequential_chain, \
                    spatial_dispersion, spatial_dispersion_r, dispersion_to_human_readable
from gui import GenericWindow, GenericImageViewer
from time import sleep
from difflib import SequenceMatcher

if __name__ == '__main__':
    g = GenericImageViewer ()
    g.show_all ()
    image = np.ndarray ((40,40,3), dtype = np.uint8)
    image.fill (0)
    #cv2.line (image, (10,20), (30,20), (255,255,255), 1, cv2.LINE_AA)
    #cv2.rectangle (image, (10,10), (30,30), (255,255,255), 1, cv2.LINE_AA)
    cv2.circle (image, (20,20), 10, (255,255,255), 1, cv2.LINE_AA)
    c = cv2.Canny (image, 200, 400)
    i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    dispersion0 = contour_to_dispersion_hash (cn [0])
    hr0 = dispersion_to_human_readable (dispersion0)
    percentage = []
    
    for angle in range (360):
        matrix = cv2.getRotationMatrix2D ((20, 20), angle ,1)
        image2 = cv2.warpAffine (image, matrix, (40, 40))
        g.set (image2)
        g.update ()
    
        c = cv2.Canny (image2, 200, 400)
        i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        #print (cn [0], len (cn [0]))
        #print (build_sequential_chain (cn [0]))
        dispersion = contour_to_dispersion_hash (cn [0])
        hr = dispersion_to_human_readable (dispersion)
        s = SequenceMatcher (None, dispersion0, dispersion)
        print (round (s.quick_ratio (), 2), dispersion, hr)
        #g.main ()
        ratio = round (s.quick_ratio (), 2)
        if ratio > .7:
            percentage.append (ratio)
        
    print (round (len (percentage) / 360, 2))

    #for a in spatial_dispersion:
        #print (a, spatial_dispersion [a])
