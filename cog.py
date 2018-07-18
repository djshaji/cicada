#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-29

from utils import debug_info

class Cog:
    input_sources = dict ()
    data_sources = dict ()
    default_database = None

    response_presets = {
        "!!": lambda self, text: None,
        "!": lambda self, text: False,
        "@": lambda self, text: True,
        "?": lambda self, text: self.process (None)
    }

    def response (self, text, module = "cog", response_type = str):
        #self.ui.info (text)
        text = "from {}: ".format (debug_info ()) + text
        
        if response_type == bool:
            text += "\n[@: True, !: False]"

        res = self.ui.get_response (message = text, module = module)
        
        if response_type == bool:
            if res == '@':
                return True
            elif res == '!!':
                return None
            else:
                return False
        
        if len (res) == 0:
            return None
        if res [0] in self.response_presets:
            return self.response_presets [res [0]] (self, text)
            #if type (self.response_presets [res [0]]) == bool:
                #return self.response_presets [res [0]]
            #elif type (self.response_presets [res [0]]) == type (lambda: True): # function
                #return self.response_presets [res [0]] (res)
        return res

    get_response = response

    def add_input (self, input, name):
        self.ui.message ("Added input source {}".format (name), "cog")
        self.input_sources [name] = input

    def add_data_source (self, source, name):
        self.ui.message ("Added data source {}".format (name), "cog")
        self.data_sources [name] = source

    def list_data_sources (self):
        msg = "The following data sources are available: "
        for d in self.data_sources:
            msg = msg + d + " "
            
        self.ui.message (msg, "cog")

    def list_input_sources (self):
        msg = "The following input sources are available: "
        for d in self.input_sources:
            msg = msg + d + " "
            
        self.ui.message (msg, "cog")

    def __init__ (self, ui):
        self.ui = ui
    
    def no_match (self, text):
        if text:
            text += "?"
        #indent this?    
        self.ui.message (text, "cog")
        self.ui.info ('no match')
    
    def match_found (self, input_source, text, module, data, data_type = None):
        if data_type == None:
            data_type = str (type (data))
        self.ui.message ("from {} {}: type {} found in module {}: {}".format (input_source, text, data_type, module, data), "cog")
        #self.ui.info ('{}: {}'.format (text, data))
        self.ui.info (input_source + ': '+ str (data))
    
    def query_data_sources (self, input_source, text):
        for source in self.data_sources:
            if self.data_sources [source].accepts_data_type (type (text)) and self.data_sources [source].query (text):
                data = self.data_sources [source].get (text)
                if data is None:
                    continue
                if type (data) == list:
                    for d in data:
                        self.match_found (input_source, text, source, d)
                        res = self.response ("OK?", response_type = bool)
                        if res is True or res is None:
                            return res
                elif type (data) == dict:
                    for d in data:
                        self.match_found (input_source, text, source, data [d], data_type = d)
                        res = self.response ("OK?", response_type = bool)
                        if res is True or res is None:
                            return res
                else:
                    self.match_found (input_source, text, source, data)
                    self.response ("OK?", response_type = bool)
                    if res is True or res is None:
                        return res
        return False
        #for source in self.data_sources:
            #if self.data_sources [source].query (text):
                #return source

    def store (self, key, value):
        #if self.default_database == None:
            #for d in self.data_sources:
                #if self.data_sources [d].is_writable ():
                    #self.default_database = self.data_sources [d]
        #if self.default_database == None:
            #self.ui.message ("No writable data source!", "cog-error")
            #return None
        
        for source in self.data_sources:
            d = self.data_sources [source]
            if not d.is_writable ():
                continue
            
            #print (d.known_data_types)
            if d.accepts_data_type (key) and d.accepts_data_type (value):
                self.ui.message ('using database ' + source, 'cog')
                d.set (key, value)
                return True
        
        self.ui.message ('No database accepts ' + str (type (key)) + ' and ' + str (type (value)) + ' data types', 'cog-error')
        #self.default_database.set (key, value)

    def process (self, text):
        if text != None:        
            if text [0] in self.response_presets:
                return self.response_presets [text [0]] (self, text)
            
            res = self.query_data_sources ("user input", text)
            if res is True or res is None:
                return res
            
        for input in self.input_sources:
            data = self.input_sources [input].poll ()
            if data is None:
                continue
            
            if self.input_sources [input].has_preview ():
                image = self.input_sources [input].get_preview (data)
                self.ui.info (data, image = image)
            else:
                self.ui.info (data)

            res = self.query_data_sources (input, data)
            if res is True or res is None:
                return res
            
            if text == None:
                if self.input_sources [input].has_preview ():
                    image = self.input_sources [input].get_preview (data)
                    self.ui.info (input + ': ' + str (data) + '?', image = image)
                else:
                    self.ui.info (input + ': ' + str (data) + '?')
                text = self.get_response ("{}: {}?".format (input, data), module = "cog")
                if text:
                    self.ui.info (input + ': ' + str (text) + '?')
            
            if text and self.get_response ("{}: {} {}?".format (text, input, data), module = "cog"):
                #self.ui.info (data)
                self.ui.message ("{} -> {}".format (text, data), "cog")
                if self.input_sources [input].has_preview ():
                    image = self.input_sources [input].get_preview (data)
                    self.ui.info ('{}: {}'.format (text, type (data).__name__), image = image)
                else:
                    self.ui.info ('{}: {}'.format (text, type (data).__name__))
                self.store (data, text)
                return
        
        self.no_match (text)
        
    
    def process1 (self, text):
        if text == None:
            self.poll ()
            return
        elif text [0] in self.response_presets and type (self.response_presets [text [0]]) == type (lambda: True): # function
            return self.response_presets [text [0]] (self, text)
        
        source = self.query_data_sources (text)
        if source:
            data = self.data_sources [source].get (text)
            self.match_found (text, source, data)
            return
        
        for input in self.input_sources:
            data = self.input_sources [input].poll ()
            if data is None:
                #self.ui.message ("input {} unavailable".format (input), "cog")
                continue
            if self.get_response ("{}: {} {}?".format (text, input, data), module = "cog"):
                self.ui.message ("{} -> {}".format (text, data), "cog")
                self.ui.info ('{}: {}'.format (text, type (data).__name__))
                return
        
        self.no_match (text)

    def poll (self):
        for input in self.input_sources:
            data = self.input_sources [input].poll ()
            if data is None:
                #self.ui.message ("input {} unavailable".format (input), "cog")
                continue
            
            source = self.query_data_sources (data)
            if source:
                res = self.data_sources [source].get (data)
                self.match_found (data, source, res)
                if self.response ("OK?"):
                    return

            text = self.get_response ("{} {}?".format (input, data), module = "cog")
            if type (text) == str and len (text) > 0:
                self.ui.message ("{} -> {}".format (text, data), "cog")
                self.ui.info ("{} -> {}".format (text, data))
                return
        
        self.no_match (None)
        
