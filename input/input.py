#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-29

class Input:
    def __init__ (self, ui):
        self.ui = ui
    
    has_preview = lambda self: hasattr (self, 'get_preview')
        
    def poll (self):
        return None

    def from_str (self):
        raise NotImplementedError
    
    def to_str (self):
        raise NotImplementedError

    probe = poll
