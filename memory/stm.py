#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-08-24

class ShortTermMemory:
    host = None
    scene = dict ()
    # scene ["x:y"] = SensoryObject

    # time of the last event
    timestamp = None # datetime.datetime

    #> Todo: some sort of virtual "scene"
    #  or graph
    #> Todo: add/merge events/sensory objects to scene

    def __init__ (self, host = None):
        self.host = host

    
