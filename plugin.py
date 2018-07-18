#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-02-09

import os, sys
import traceback
from glob import glob
from importlib import import_module

# question: to be or not to be?
# do we store plugins as Plugins or Plugins ()?
# do we store classes or objects?
# if we create objects, we have to restart the
# program to run the code again
# so we store classes
# this is the desired behavior
# if i ever get confused
# which i will 0_0

class PluginHost:
    path = None
    manager = None
    modules = None # dict ()
    
    def get_plugins (self):
        plugins = list ()
        for a in self.modules:
            plugins.append (a)
        return plugins

    def __init__ (self, ui = None, auto_load = True):
        self.ui = ui
        self.modules = dict ()
        self.path = os.path.join (os.getcwd (), 'plugins')
        if auto_load:
            self.auto_load ()

        for i in self.modules:
            self.ui.entry_completion_store.set_value (self.ui.entry_completion_store.append (), 0, "%" + i)
        
    def load (self, filename):
        module = import_module (filename)
        plugin = getattr (module, 'Plugin')
        self.modules [filename.split ('.') [-1]] = plugin
        
    def auto_load (self, path = None):
        if not path:
            path = self.path
        
        files = glob (self.path + "/*py")
        for f in files:
            self.load ('plugins.' + os.path.basename (f).split ('.') [0])

    def run (self, plugin):
        assert plugin in self.modules
        plugin = self.modules [plugin] ()
        setattr (plugin, 'host', self)
        setattr (plugin, 'ui', self.ui)
    
        #return plugin.run ()
        # the following does not return line no
        try:
            res = plugin.run ()
        except Exception as e:
            #self.ui.error (str (e))
            #print (e)
            print (traceback.print_exc ())
            return str (e)
        return res

if __name__ == '__main__':
    p = PluginHost ()
    p.auto_load ()
    p.run ('test')
