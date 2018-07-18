#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-08-16

from gi.repository import GLib

class SensoryInput:
    ui = None
    # -20 to 20
    priority = GLib.PRIORITY_DEFAULT
    # in milliseconds
    poll_interval = 300
    
    # if poll returns null, or the system is otherwise
    # suspended, sleep for this number of **seconds**
    poll_suspend_interval = 5

    #def monitor (self):
        #pass

    def __init__ (self, ui = None):
        self.ui = ui
    
    def poll (self):
        return None

    def search (self):
        raise NotImplementedError


class SensoryObject:
    initiator = None
    initiator_type = SensoryInput
    #source = None
    #source_type = SensoryInput

    name = None

    location = None
    shape = None
    location_probability = 0 # %
    shape_probability = 0 #%
    scale = 1

    properties = None
    orientation = None
    
    
