#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  2016-09-06

from input.visual import cv2_image_to_gdk_pixbuf

class BridgeInput:
    def close (self):
        pass
    
    def get_focus (self, pixbuf = False):
        image = None
        if self.ui:
            image = self.ui.camera_get_focus ()
        elif self.manager:
            image = self.manager.ui_instances [self.id].camera_get_focus ()
        
        #print (type (image), image.shape)
        if pixbuf:
            return cv2_image_to_gdk_pixbuf (image)
        else:
            return image
    
    def get_pixbuf (self):
        if self.focus_only:
            return self.get_focus (pixbuf = True)
            
        #print (self.manager.ui_instances [self.id].get_frame (focused = True, pixbuf = True))
        if self.ui:
            return self.ui.get_frame (focused = True, pixbuf = True)
        elif self.manager:
            return self.manager.ui_instances [self.id].get_frame (focused = True, pixbuf = True)
        else:
            return None

    def __init__ (self, ui = None, manager = None, id = 0, focus_only = False):
        self.ui = ui
        self.focus_only = focus_only
        self.manager = manager
        self.id = id
        self.get_frame = self.poll
        #print (ui, manager, id)
    
    def set_ui_id (self, id = 0):
        self.id = id
        
    def poll (self):
        if self.focus_only:
            return self.get_focus ()
            
        if self.ui:
            return self.ui.get_frame (focused = True)
        elif self.manager:
            return self.manager.ui_instances [self.id].get_frame (focused = True)
        else:
            return None

    
    
