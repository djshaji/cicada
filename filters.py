#!/usr/bin/env python3
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-07-02
# Filters

import os
from glob import glob
from importlib import import_module

class Filter:
    #arg1 = 0
    #arg2 = str ()
    
    ui = None

    def __init__ (self, ui = None):
        if ui:
            self.ui = ui
    
    def getopts (self):
        #return [['arg1', int], ['arg2', str]]
        #return [
        #   ["name", int, min, max, step, default],
        #   ["name", str, val1, val2, val3, default]
        return []

    def filter (self, image):
        return image

class FilterHost:
    path = "filters"
    filters = None # dict ()

    def __init__ (self, ui = None):
        self.ui = ui
        self.filters = dict ()
        self.path = os.path.join (os.getcwd (), 'filter')
        self.load_all ()

    def load (self, filename):
        module = import_module (filename)
        for d in dir (module):
            if not d [0] == '_' and not d == "Filter" and not d == "cv2": #hack!
                # pay attention what we're doing here
                # we instantiate only one instance of 
                # filter () here!
                # as opposed to what we do with plugins
                self.filters [d] = getattr (module, d) (self.ui)
                
    def load_all (self, path = None):
        if not path:
            path = self.path
        
        files = glob (self.path + "/*py")
        for f in files:
            self.load ('filter.' + os.path.basename (f).split ('.') [0])

if __name__ == '__main__':
    p = FilterHost ()
    p.load_all ()
    for a in p.filters:
        print (a)
