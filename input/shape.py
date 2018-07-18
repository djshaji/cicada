#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-08-04

import cv2
import numpy as np
from input.input import Input
from input.contour import Contour, copy_contour_multi, contour_frame_get_mean_color, contour_to_dispersion_hash, dispersion_to_contour, generate_image_from_contour, contour_get_mean_color, copy_contour_multi
from colour import Color
from input.color import get_mean_color_multi
from storage.zodb import ZODBDataSource

class Shape:
    dispersion = None
    color = None
    
    def __init__ (self, dispersion, color):
        self.dispersion = dispersion
        self.color = color
    
    def __str__ (self):
        return str (self.dispersion) + ' ' + str (self.color)

class ShapeInput (Input):
    def get_preview (self, shape, size = -1):
        if size == -1:
            size = self.ui.PREVIEW_ICON_SIZE

        im1 = np.ndarray ((size, size , 3), dtype = np.uint8)
        c = Color (shape.color)
        im1 [:] = (c.blue * 255, c.green * 255, c.red * 255)

        c = Color (shape.color)
        b = c.blue * 255
        g = c.green * 255
        r = c.red * 255
        im2 = generate_image_from_contour (dispersion_to_contour (str (shape.dispersion), scale = 5), fg = (b, g, r))
        im2 = cv2.resize (im2, (im1.shape [1], im1.shape [1]))
        #print (im1[:][size:].shape, im2.shape)
        #im1 [:][size:] = im2 [:][:]
        return np.append (im1, im2, axis = 1) # [:size][:] + im2#cv2.add (im1, im2)

    def poll (self):
        cn = self.ui.get_focus (raw = True)
        image = self.ui.get_frame ()
        if cn is None:
            return None
        elif not isinstance (cn, np.ndarray):
            return None
        elif cn.shape [2] != 2:
            return None
        
        dispersion = contour_to_dispersion_hash (cn)
        #color = contour_frame_get_mean_color (image, cn)
        color = contour_get_mean_color (image, cn)
        return Shape (dispersion, color)
        #return Contour (dispersion)
        
        
class ShapeStorage (ZODBDataSource):
    def __init__ (self, ui):
        self.ui = ui
        self.known_data_types = [str, Shape]
    
    def set (self, shape, name):
        assert isinstance (shape, Shape) and isinstance (name, str)
        self.open () if self.root is None else True
        
        self.storage.link (["type", "shape", name, "Color", str (shape.color)], ["type", "Color", str (shape.color)])
        self.storage.link (["type", "shape", name, "contour", str (shape.dispersion)], ["type", "contour", str (shape.dispersion)])
        self.storage.link (['type', 'Color', str (shape.color), 'shape', name], ['type', 'shape', name])
        self.storage.link (['type', 'contour', str (shape.dispersion), 'shape', name], ['type', 'shape', name])
        self.storage.commit ()
        
    def get (self, shape):
        self.open () if self.root is None else True
        if isinstance (shape, str):
            color = self.storage.get ("type", "shape", shape, "Color") [0]
            contour = self.storage.get ("type", "shape", shape, "contour") [0]
            return Shape (contour, color)
        elif isinstance (shape, Shape):
            colors = self.storage.get ('type', 'Color', str (shape.color), 'shape')
            contours = self.storage.get ('type', 'contour', str (shape.dispersion), 'shape')
            
            for cl in colors:
                if cl in contours:
                    return cl
            return None
        else:
            return None

    def query (self, shape):
        self.open () if self.root is None else True
        if isinstance (shape, str):
            color = self.storage.get ("type", "shape", shape, "Color")
            contour = self.storage.get ("type", "shape", shape, "contour")
            if color and contour:
                return True
            else:
                return False
        elif isinstance (shape, Shape):
            colors = self.storage.get ('type', 'Color', str (shape.color), 'shape')
            contours = self.storage.get ('type', 'contour', str (shape.dispersion), 'shape')
            
            if colors and contours:
                for cl in colors:
                    if cl in contours:
                        return True
            return False
        else:
            return False

        
