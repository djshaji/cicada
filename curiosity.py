#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-08-16

from gi.repository import GLib
from utils import debug
from memory.stm import ShortTermMemory

class Curiosity:
    ui = None
    mainloop = None
    sensory_inputs = None
    stm = None

    def stm_update (self, event):
        pass
    
    def register_sensory_input (self, sensory_input):
        self.sensory_inputs.append (sensory_input)

    def __init__ (self, ui):
        self.ui = ui
        self.sensory_inputs = []
        self.mainloop = GLib.MainLoop ()
        self.stm = ShortTermMemory (self)

    def main (self):
        self.ui.message ("Curiosity online")
        for i in self.sensory_inputs:
            self.poll_sensory_input_hook (i)
        
        #debug ("main loop started")
        #self.mainloop.run ()

    def poll_sensory_input_hook (self, system):
        self.ui.message ("Loaded subsystem: " + str (system))
        GLib.timeout_add (system.poll_interval, lambda *w: self.poll_sensory_input (system), None)
        return False
    
    def poll_sensory_input (self, system):
        event = system.poll ()
        if event == None:
            #GLib.timeout_add (system.priority, system.poll_suspend_interval, lambda *w: self.poll_sensory_input_hook (system))
            GLib.timeout_add (system.poll_suspend_interval, lambda *w: self.poll_sensory_input_hook (system))
            return False
        else:
            system.monitor (event.raw_data)
            # process data here
            #debug ("processing data from {}".format (system))
            return True
        
