#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-24

from version import version

class HashCommands:
    def __init__ (self, gui):
        self.ui = gui
    
    def append (self, command, function):
        self.commands [command]= function

    def help (self):
        h = "Following commands are available:\n"
        for i in self.commands:
            if len (i) > 1:
                h = h + i + " "
        return h
        
    
    def run (self, command):
        if len (command) is 1:
            return self.help ()
        
        command = command [1:]
        command = command.split (";")

        if command [0] in self.commands:
            self.ui.message (command [0], 'hash')
            if len (command) is 1:
                return self.commands [command [0]] (self)
            else:
                return self.commands [command [0]] (self, command [1:])
        else:
            self.ui.message ("No command {} available!".format (command), "hash-error")
            return None

    commands = {
        "": lambda self: self.help (),
        "help-commands": lambda self: self.help (),
        "version": lambda self: version,
        "quit": lambda self: self.ui.main_quit ()
    }
    
