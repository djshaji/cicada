#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-30

from multiprocessing import Process, Queue, pool
import multiprocessing
from time import perf_counter
import inspect
from os.path import basename

def debug_info ():
    (frame, filename, line_number, function_name, lines, index) = inspect.getouterframes (inspect.currentframe()) [2]
    return "{}:{} {}".format (basename (filename).split (".") [0], line_number, function_name)

def debug (* args):
    s = debug_info () + "> "
    for a in args:
        s += str (a) + ' '
    print (s)

class Timer:
    precision = 2
    def __init__ (self):
        self.epoch = perf_counter ()
    
    def time (self):
        t = perf_counter () - self.epoch
        if self.precision:
            return round (t, self.precision)
        else:
            return t

    def reset (self):
        self.epoch = perf_counter ()

class Thread:
    queues = None # []
    processes = None # []
    threads = 4 # default
    target = None # ()
    args = None
    return_data = None # []
    
    def __init__ (self, threads, target, args):
        self.queues = []
        self.processes = []
        self.threads = threads
        self.target = target
        self.args = args
        self.return_data = []
        self.initialize ()

    def initialize (self):
        for x in range (self.threads):
            p = Process (target = self.target, args = (self, x))
            q = Queue ()
            self.processes .append (p)
            self.queues.append (q)
            
    def start (self):
        for t in range (self.threads):
            self.processes [t].start ()

    def join (self):
        for t in range (self.threads):
            self.processes [t].join ()
    
    def get_data (self):
        for t in range (self.threads):
            self.return_data.append (self.queues [t].get ())
            
        return self.return_data

def enter ():
    (frame, filename, line_number, function_name, lines, index) = inspect.getouterframes (inspect.currentframe()) [1]
    filename = basename (filename).split ('.') [0]
    msg = '>>> {} [{}]: {}'.format (filename, line_number, function_name)
    print (msg)
    return msg

def leave ():
    (frame, filename, line_number, function_name, lines, index) = inspect.getouterframes (inspect.currentframe()) [1]
    filename = basename (filename).split ('.') [0]
    msg = '<<< {} [{}]: {}'.format (filename, line_number, function_name)
    print (msg)
    return msg

#class MultiProcess:
    ## aim: take a function name, list of data,
    ## run function on data, return result
    #queues = None # []
    #processes = None # []
    #threads = 4 # default
    #func = None
    #data = None # []
    #return_data = None # []
    
    #def __init__ (self, func, data, threads = 4):
        ## make sure data is a _list_
        ## heh
        #assert hasattr (data, "__len__")
        
        #self.queues = []
        #self.processes = []
        #self.threads = threads
        #self.func = func
        #self.data = data
        #self.return_data = []
        #self.initialize ()

    #def initialize (self):
        #for x in range (self.threads):
            #p = Process (target = self.target, args = (self, x))
            #q = Queue ()
            #self.processes.append (p)
            #self.queues.append (q)
            
    #def start (self):
        #for t in range (self.threads):
            #self.processes [t].start ()

    #def join (self):
        #for t in range (self.threads):
            #self.processes [t].join ()
    
    #def get_data (self):
        #for t in range (self.threads):
            #self.return_data.append (self.queues [t].get ())
            
        #return self.return_data

class Pool(multiprocessing.pool.Pool):
    class Process(multiprocessing.Process):
        # make 'daemon' attribute always return False
        def _get_daemon(self):
            return False
        def _set_daemon(self, value):
            pass
            
        daemon = property(_get_daemon, _set_daemon)
    
