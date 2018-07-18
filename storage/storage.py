#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-29

class Storage:
    known_data_types = None
    #accepts_data_type = lambda self, data_type: data_type in self.known_data_types
    is_writable = lambda self: hasattr (self, "set")

    def accepts_data_type (self, data_type):
        assert self.known_data_types is not None
        if not type (data_type) is type:
            data_type = type (data_type)
        
        if data_type in self.known_data_types:
            return True
        else:
            return False
    
    def __init__ (self, ui):
        self.ui = ui
        pass

    def query (self, text):
        return None
    
    def get (self, text):
        return None
