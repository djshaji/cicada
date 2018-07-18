#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-29

from pathlib import Path

def discover_modules (module):
    path = Path (module)
    files = path.glob ("*.py")
    
    imported = []
    
    for f in files:
        module_name = str (f).split ('.')[0]
        imported_as = module_name [:1].upper () + module_name [1:]
        imported.append ([module_name, imported_as])
        print (module_name)
        import module_name as imported_as

    return imported
