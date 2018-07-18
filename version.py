#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-24

import os, time

build_version = "sphinx-2017.3"

def get_version ():
    t = time.localtime (os.path.getmtime ('.'))
    return build_version + '-{}.{}.{}'.format (t.tm_mday, t.tm_mon, t.tm_year)

version = get_version ()
