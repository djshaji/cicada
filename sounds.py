#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-01-28

import os

class Sounds:
    default_dir = '/mnt/sda2/Windows/Media/'
    sounds = {
        'default': 'Windows Navigation Start.wav',
        'error': 'Windows Error.wav',
        #'error': 'Windows Exclamation.wav',
        'chimes': 'chimes.wav',
        'notify': 'notify.wav',
        'chord': 'chord.wav'
    }
    
    enabled = True
    
    def __init__ (self):
        if not os.path.exists (self.default_dir):
            self.enabled = False
    
    def play_file (self, filename):
        cmd = 'paplay "{}"&'.format (filename)
        os.system (cmd)
    
    def play (self, media):
        if not self.enabled or not media in self.sounds:
            return False
        
        filename = os.path.join (self.default_dir, self.sounds [media])
        self.play_file (filename)
        return True
    
if __name__ == '__main__':
    s = Sounds ()
    s.play ('notify')
