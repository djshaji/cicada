#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-08-11
#  Python is awesome.
#  If any mortal but need proof, let him look no more
#  The real MVP, right here

import types
import sys, warnings
import copy

class IntrospectionDefaultNamespace:
    pass

class Introspection:
    modules = None # []
    function_types = types.BuiltinFunctionType, types.MethodType
    
    def __init__ (self, ui = None, modules = None):
        assert modules is None or isinstance (modules, tuple)
        
        self.default_namespace = IntrospectionDefaultNamespace ()
        self.ui = ui
        self.modules = [self.default_namespace]
        self.add_module = self.modules.append
        
        if modules:
            for m in modules:
                self.modules.append (m)
        
    def find (self, what, return_module = False):
        # remember this is here !
        # don't fret later on wondering where your
        # whitespace went !
        what = what.replace (' ', '')

        for m in self.modules:
            if hasattr (m, what):
                if return_module:
                    return m, what
                else:
                    return getattr (m, what)
            elif '.' in what:
                vector = what.split ('.')
                if not hasattr (m, vector [0]):
                    continue
                
                attr = vector [1]
                name = m
                mod = m
                for v in vector:
                    if hasattr (name, v):
                        mod = name
                        name = getattr (name, v)
                        attr = v
                    else:
                        name = None
                        break
                if return_module:
                    return mod, attr
                else:
                    return name
        return None

    def is_function (self, name):
        for t in self.function_types:
            if isinstance (name, t):
                return True
        return False

    def is_attr (self, name):
        for m in self.modules:
            if hasattr (m, str (name)):
                return True
        return False

    def parse_value (self, what):
        if not len (what):
            return None

        # remember this is here !
        # don't fret later on wondering where your
        # whitespace went !
        what = what.replace (' ', '')
        
        if ',' in what or (what [0] == '(' or what [0] == '[') or  (',' in what and what [0] == '(' or  what [0] == '['):
            value = []
            if what [0] == '[' or what [0] == '(':
                what = what [1:]
            if what [-1] == ']' or what [-1] == ')':
                what = what [:-1]
            
            what = what.split (',')
            for w in what:
                v = self.parse_value (w)
                if v is not None:
                    value.append (v)
            
            return value
        
        if what.isdigit ():
            return int (what)
        elif what [0] == '-' and what [1:].isdigit ():
            # waow
            return int (what)
        
        return what

    def assign (self, text):
        assert '=' in text
        
        # remember this is here !
        # don't fret later on wondering where your
        # whitespace went !
        text = text.replace (' ', '')
        
        vector = text.split ('=', 1)
        what = self.find (vector [0], return_module = True)
        to = self.parse_value (vector [1])
        #print (type ( to))
        if not what:
            what = vector [0]
            setattr (self.default_namespace, what, to)
            #what = getattr (self.default_namespace, what)
        else:
            setattr (what [0], what [1], to)
            #print (getattr (what [0], what [1]))
            #print (what)
            #what = to
        #print (self.find (vector [0]), to)
        return what, to

    def introspect (self, command):
        if len (command) == 1:
            if '=' in command [0]:
                return self.assign (command [0].replace (' ', ''))
        
        names = None
        
        if isinstance (command, str):
            names = command.split (';')
        elif isinstance (command, tuple):
            names = command
        elif isinstance (command, list):
            names = command
        else:
            raise NotImplementedError

        chain = []
        for name in names:
            what = self.find (name)
            if what:
                chain.append (what)
            else:
                chain.append (self.parse_value (name))

        retval = None
        for i in range (len (chain) - 1, -1, -1):
            if retval is None:
                if self.is_function (chain [i]):
                    retval = chain [i] ()
                #elif self.find (chain [i]):
                #else:
                elif not len (chain) == 1:
                    retval = chain [i]
                elif not chain [i] is names [-1]:
                    retval = chain [i]
                else:
                    self.ui.message ('name not found: ' + names [-1], 'introspect-error')
            elif self.is_function (chain [i]):
                if isinstance (retval, list):
                    retval = chain [i] (retval)
                else:
                    if isinstance (retval, list) or isinstance (retval, tuple):
                        retval = chain [i] (*retval)
                    else:
                        retval = chain [i] (retval)
            else:
                retval = chain [i], retval
        
        return retval

    def get_completion (self, module = None, recurse = True, depth = 0):
        # might be broken for depth > 2
        attrs = []
        
        if module is None:
            module = self.modules
 
        for m in module:
            # i love python
            attrs += dir (m)
        if recurse:
            while depth > 0:
                depth -= 1
                for a in copy.copy (attrs):
                    if a [0] == '_':
                        continue
                    try:
                        if hasattr (m, a):
                            ret = self.get_completion (module = [getattr (m, a)], depth = depth)
                            for r in ret:
                                attrs.append (a + '.' + r)
                    except Exception as e:
                        warnings.warn (str (e))
        return attrs
            

if __name__ == '__main__':
    i = Introspection ()
    i.add_module (__builtins__)
    print (i.introspect (sys.argv [1]))
    pass
