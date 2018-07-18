#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-08-18

import datetime

class Event:
    event_type = None
    # sensory system which initiated the event
    initiator = None
    
    # e.g. cv2 image
    raw_data = None
    
    # datetime.datetime
    timestamp = None

    scene = None
    
    # e.g. what tensor flow might return
    interpreted_data = None
    
    # high level (!) object recognition
    #name = None # object
    #action = None
    # now we have more than one object
    # in one event
    # event will model stm
    # stm is difference of last event and events
    # before that. as in *humans*
    
    def __init__ (self, initiator):
        self.initiator = initiator
        self.event_type = type (initiator)
        self.timestamp = datetime.datetime.now ()
        self.scene = dict ()
