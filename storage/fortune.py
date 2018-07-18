#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-29

from storage.storage import Storage
from subprocess import check_output as exec

class Fortune (Storage):
    def __init__ (self, ui):
        #super (Fortune, self).__init__ (ui)
        self.ui = ui
        self.known_data_types = [str]
        self.get = self.get_fortune

    def query (self, text):
        if text == "fortune":
            return True
        else:
            return False
    
    def get_fortune (self, text):
        return exec ("fortune", universal_newlines = True)
        
        

if __name__ == '__main__':
    f = Fortune ()
    print (f.get_fortune ())
    
