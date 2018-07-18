#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-01-27
#
# Plug-in module for FAST: Features from Accelerated Segment Test

# note here:
# this module _currently_ uses config options
# from contourfocus ui. I'm saying this here
# so I don't have to do this:
#if hasattr (self.ui, 'contourfocus'):
    #img2 = cv2.drawKeypoints(selection, key_points, img2, color = self.ui.contourfocus.selection_color)
#else:
    #img2 = cv2.drawKeypoints(selection, key_points, img2, color = (255,255,255))

# todo:
# use the common cv2 feature detector interface
# hopefully the system will automatically
# select an appropriate detector
# someday!

import numpy as np
import cv2
from enum import Enum
from input.contour import translate_coordinates, generate_image_from_contour, copy_contour_rectangle, contour_get_mean_color_multi

def key_points_to_contour (key_points):
    cn = np.ndarray ((len (key_points), 1, 2), int)
    for c in range (len (cn)):
        cn [c] = key_points [c].pt
    
    return cn


class FastFocus:
    fast = None
    draw_only_key_points = False
    
    class Types (Enum):
        type_5_8 = cv2.FAST_FEATURE_DETECTOR_TYPE_5_8
        type_7_12 = cv2.FAST_FEATURE_DETECTOR_TYPE_7_12
        type_9_16 = cv2.FAST_FEATURE_DETECTOR_TYPE_9_16
    
    #def set (self, nms = True, ftype = cv2.FAST_FEATURE_DETECTOR_TYPE_9_16, threshold = 10):
    def set (self, nms = None, ftype = None, threshold = None, draw_only_key_points = None):
        # Non Max Supression
        if nms is not None:
            self.fast.setNonmaxSuppression (nms)
        if ftype is not None:
            self.fast.setType (ftype)
        if threshold is not None:
            self.fast.setThreshold (threshold)
        if draw_only_key_points is not None:
            self.draw_only_key_points = draw_only_key_points
    
    def __init__ (self, ui = None):
        if ui:
            self.ui = ui
        
        self.fast = cv2.FastFeatureDetector_create ()
        self.getNonmaxSuppression = self.fast.getNonmaxSuppression
        self.getType = self.fast.getType
        self.getThreshold = self.fast.getThreshold
    
    def detect (self, image):
        # We do this here, so we have to change it
        # only once
        return self.fast.detect (image, None)
    
    def draw (self, image, es = False):
        #img2 = None
        img2 = np.ndarray (image.shape, image.dtype)
        #img2.fill (0)
        img2 [:] = image [:]
        key_points = self.detect (image)
        cn = key_points_to_contour (key_points)
        color = (255, 255, 255)
        # aye!
        # bring in colors from contour focus ui
        
        if self.draw_only_key_points:
            image.fill (0)
            img2.fill (0)
        
        if es:
            center, side = self.ui.get_focus_coords ('color')
            x = center [0] - side [0]
            y = center [1] - side [1]
            x2 = center [0] + side [0]
            y2 = center [1] + side [1]
            #selection = copy_contour_rectangle (image, x, y, side [0], side [1]).astype (np.uint8)
            #key_points = self.fast.detect (selection, None)
            #img2 = cv2.drawKeypoints(image, key_points, img2, color = self.ui.contourfocus.selection_color)
            cv2.drawContours (img2, cn, -1, self.ui.contourfocus.selection_color, self.ui.contourfocus.thickness)
            image [y:y2, x:x2] = img2 [y:y2, x:x2]
            image = cv2.rectangle (image, (x,y), (x2,y2), self.ui.contourfocus.es_color, self.ui.contourfocus.thickness if self.ui.contourfocus.thickness > 0 else abs (self.ui.contourfocus.thickness))
            return image

        #img2 = cv2.drawKeypoints(image, key_points, img2, color = self.ui.contourfocus.selection_color)        
        cv2.drawContours (img2, cn, -1, self.ui.contourfocus.selection_color, self.ui.contourfocus.thickness)
        return img2

    def get (self, image, raw = False, es = False):
        key_points = self.fast.detect (image, None)
        cn = key_points_to_contour (key_points)
        
        if not len (cn):
            return None

        if raw:
            if es:
                cn = self.ui.colorfocus.get (None, raw = True)
                if cn is None or not len (cn):
                    return None

                kp = []
                for p in range (len (key_points)):
                    if cv2.pointPolygonTest (cn, key_points [p].pt, False) >= 0:
                        kp.append (key_points [p])
                return kp
            else:
                return key_points                
        
        image.fill (255)
        cv2.drawContours (image, cn, -1, self.ui.contourfocus.selection_color, self.ui.contourfocus.thickness)
        if es:
            center, side = self.ui.get_focus_coords ('color')
            x = center [0] - side [0]
            y = center [1] - side [1]
            x2 = center [0] + side [0]
            y2 = center [1] + side [1]
            return image [y:y2, x:x2]
        return image

class OrbFocus:
    # next time inherit instead of creating
    # an object
    # OrbFocus (cv2.ORB) instead of
    # orbfocus.orb
    orb = None
    
    def __init__ (self, ui = None):
        self.orb = cv2.ORB_create ()
        self.ui = ui
    
    def get (self, image, es = False, raw = False):
        key_points, descriptors = self.orb.detectAndCompute (image, None)
        cn = key_points_to_contour (key_points)
        
        if cn is None or len (cn) == 0:
            return None

        if raw:
            if es:
                #raise NotImplementedError
                cn = self.ui.colorfocus.get (None, raw = True)
                if cn is None or not len (cn):
                    return None

                # because we cannot modify (numpy) arrays while we're
                # iterating them, therefore this
                #kp = np.ndarray ((0, key_points [0].shape [1]), np.uint8)
                kp = []
                des = np.ndarray ((0, 32), np.uint8)
                for p in range (len (key_points)):
                    if cv2.pointPolygonTest (cn, key_points [p].pt, False) >= 0:
                        #kp = np.append (kp, key_points, 0)
                        kp.append (key_points [p])
                        des = np.append (des, descriptors, 0)
                return kp, des
            else:
                return key_points, descriptors                
        
        # this right here is a problem
        # because if we generate a new image,
        # then coordinates won't match any more
        #image = generate_image_from_contour (cn, bg = bg, fg = fg)
        image.fill (255)
        cv2.drawContours (image, cn, -1, self.ui.contourfocus.selection_color, self.ui.contourfocus.thickness)
        if es:
            center, side = self.ui.get_focus_coords ('color')
            x = center [0] - side [0]
            y = center [1] - side [1]
            x2 = center [0] + side [0]
            y2 = center [1] + side [1]
            return image [y:y2, x:x2]
        return image

    
    def draw (self, image, es = False):
        img2 = np.ndarray (image.shape, image.dtype)
        img2 [:] = image [:]
        try:
            key_points = self.orb.detect (image)
        except Exception as e:
            self.ui.message (str (e), 'ui-error')
            print (e)
            return
        
        #print (key_points)
        cn = key_points_to_contour (key_points)
        color = (255, 255, 255)
        
        if self.ui.fastfocus.draw_only_key_points:
            image.fill (0)
            img2.fill (0)
        
        if es:
            center, side = self.ui.get_focus_coords ('color')
            x = center [0] - side [0]
            y = center [1] - side [1]
            x2 = center [0] + side [0]
            y2 = center [1] + side [1]
            cv2.drawContours (img2, cn, -1, self.ui.contourfocus.selection_color, self.ui.contourfocus.thickness)
            image [y:y2, x:x2] = img2 [y:y2, x:x2]
            image = cv2.rectangle (image, (x,y), (x2,y2), self.ui.contourfocus.es_color, self.ui.contourfocus.thickness if self.ui.contourfocus.thickness > 0 else abs (self.ui.contourfocus.thickness))
            return image

        cv2.drawContours (img2, cn, -1, self.ui.contourfocus.selection_color, self.ui.contourfocus.thickness)
        return img2
        
