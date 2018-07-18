#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-08-16


from input.sensoryinput import SensoryInput
from event import Event

class VisualSensoryInput (SensoryInput):
    # ah, Python
    # my one true love
    
    def __str__ (self):
        return "Visual"

    def monitor (self, image):
        self.ui.set_image (image)

    def poll (self):
        event = Event (type (self), self)
        event.raw_data = self.ui.poll_image ()

        return event
        #if type (event.raw_data) == np.ndarray:
            #return event
        #else:
            #return None
        
