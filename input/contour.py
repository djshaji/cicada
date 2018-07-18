#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-07-05

import sys, os, multiprocessing
from warnings import warn
import cv2, numpy as np
from random import randrange, uniform
from enum import Enum
import copy
import persistent
import BTrees.OOBTree
from storage.zodb import ZODBDataSource
from input.input import Input
from utils import Thread, debug_info, debug
from difflib import SequenceMatcher
from input.color import get_mean_color_multi
from colour import Color
from utils import enter, leave
from difflib import SequenceMatcher

spatial_dispersion = dict ()
spatial_dispersion_r = dict ()

counter = 0

for i in range (-1, 2):    
    for j in range (-1, 2):
        spatial_dispersion [(i, j)] = counter
        spatial_dispersion_r [counter] = (i,j)
        counter += 1

human_readable_codes_for_dispersion = {
    0: '↖', #' <^ ',
    1: '←', #'<',
    2: '↙',#'<v',
    3: '↑',#'^',
    4: '∙',#'.',
    5: '↓',#'v',
    6: '↗',#' ^> ',
    7: '→',#'>',
    8: '↘', #' v> '
    '↖': 0, #' <^ ',
    '←': 1, #'<',
    '↙': 2,#'<v',
    '↑': 3,#'^',
    '∙': 4,#'.',
    '↓': 5,#'v',
    '↗': 6,#' ^> ',
    '→': 7,#'>',
    '↘': 8 #' v> '    
}

dispersion_proxima = {
    0: (1, 3, 4),
    1: (0, 2, 4),
    2: (1, 5, 4),
    3: (0, 6, 4),
    4: (1,2,3,4,5,6,7,8), #wut?
    5: (2, 8, 4),
    6: (7, 3, 4),
    7: (6, 8, 4),
    8: (7, 5, 4),
    '↖': ('←', '↑', '∙'),
    '←': ('↖', '↙', '∙'),
    '↙': ('←', '↓', '∙'),
    '↑': ('↖', '↗', '∙'),
    '∙': ('↖', '↑', '↗', '→', '↘', '↓', '↙', '←'),
    '↓': ('↙', '↘', '∙'),
    '↗': ('→', '↑', '∙'),
    '→': ('↘', '↗', '∙'),
    '↘': ('→', '↓', '∙')
}

def contour_fix_orientation (d1, d2):
    #debug (d1, d2)
    s = SequenceMatcher (None, d1, d2)
    m = s.get_matching_blocks ()
    m.sort () # ok wow
    #debug (m [0][2]) # size
    # no match
    if m [0][2] == 0:
        return d1, d2
    
    m = m [0]
    d1 = d1 [m [0]: -1] + d1 [: m[0]]
    d2 = d2 [m [1]: -1] + d2 [: m[1]]

    #debug (d1, d2)
    return d1, d2
    
def match_contour_dispersion (d1, d2):
    probability = 0
    
    l1 = len (d1)
    l2 = len (d2)
    
    if l2 > l1:
        l1, l2 = l2, l1
        d1, d2 = d2, d1
    
    # normalize to some extent so that their len ()
    # matches a little
    # like this:
    # normalize (d1, d2)
    
    # and we have it
    # (to some extent)
    dispersion_reduce (d2, length = l1)
    d1, d2 = contour_fix_orientation (d1, d2)
    
    l1 = len (d1)
    l2 = len (d2)
    
    for i in range (l1):
        if i >= l2:
            break
        
        if d2 [i] in dispersion_proxima [d1 [i]]:
            probability += 1
            # maybe increment more than one
            # depending on certain factors?
    
    if l1 > l2:
        return round ((probability / l1) * 100, 2)
    else:
        return round ((probability / l2) * 100, 2)
    
def dispersion_reduce (dispersion, factor = 1, length = 0, margin = 100):
    count = 0
    
    while (count < factor):
        res = str ()
        l = len (dispersion)
        for i in range (l):
            #if i < l - 1 and dispersion [i + 1] in dispersion_proxima [dispersion [i]]:
                #res += dispersion [i]
            if i % 2 == 0:
                res += dispersion [i]
        dispersion = res
        #print (l, length)
        if length and l - length <= margin:
            break
        elif not length:
            count += 1

    return dispersion

def contour_nearest_points (cn1, cn2):
    px = abs (cn1 [0][0][0] - cn2 [0][0][0])
    py = abs (cn1 [0][0][1] - cn2 [0][0][1])
    m1 = cn1 [0][0]
    m2 = cn2 [0][0]
    
    for x in range (len (cn1)):
        # because contours are like this
        # [[146  52]]
        c1 = cn1 [x]
        a = c1 [0]
        for y in range (len (cn2)):
            c2 = cn2 [y]
            b = c2 [0]
            if abs (a [0] - b [0]) < px and abs (a [1] - b [1]) < py:
                px = abs (a [0] - b [0])
                py = abs (a [1] - b [1])
                m1 = a
                m2 = b
               
    return (list (m1), x, list (m2), y)


def contour_stitch (cn1, cn2):
    # return the nearest points
    # nearest point of cn1, index in list1,
    # nearest point of cn2, index in list2
    m1, x, m2, y = contour_nearest_points (cn1, cn2)
    cn = np.ndarray ((0,1,2))
    cn = cn1 [:x]
    cn = np.append (cn, cn2 [:y], 0)
    return cn
    
    

def sort_contours (a, b):
    return len (a) - len (b)

def get_min_coordinates (cn):
    x = []
    y = []
    for c in cn:
        x .append (c [0][0])
        y .append (c [0][1])
    
    return min (x), min (y)

def translate_coordinates (cn, xy, reverse = False):
    if isinstance (cn, list):
        res = []
        for c in cn:
            res.append (translate_coordinates (c, xy, reverse))
        return res

    if not reverse:
        res = np.ndarray (cn.shape, dtype = int)
        for i in range (len (cn)):
            res [i][0][0] = cn [i][0][0] - xy [0]
            res [i][0][1] = cn [i][0][1] - xy [1]
        return res
    else:
        res = np.ndarray (cn.shape, dtype = int)
        for i in range (len (cn)):
            res [i][0][0] = cn [i][0][0] + xy [0]
            res [i][0][1] = cn [i][0][1] + xy [1]
        return res

def do_contours (filename, compare_to):
    im = cv2.imread (compare_to, -1)
    compare = cv2.imread (filename)
    c = cv2.Canny (im, 100, 200)
    compare_canny = cv2.Canny (compare, 100, 200)
    cv2.namedWindow('test')
    i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    i, cn_comparison, hr = cv2.findContours (compare_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    img = np.ndarray (im.shape, dtype = im.dtype)
    img.fill (0)
    cn.sort (key = len, reverse = True)
    cn_comparison.sort (key = len, reverse = True)
    
    for cn_compare in cn_comparison:
        for i in range (len (cn)):
            print ('{} of {}: {}'.format (i, len (cn) - 1, len (cn [i])))
            img.fill (0)
            cv2.drawContours (img, cn, -1, (150, 150,150), 1)
            cv2.drawContours (img, cn, i, (uniform (.7, 1) * 255, uniform (.7, 1) * 255, uniform (.7, 1) * 255), 2)
            cv2.drawContours (img, cn_compare, -1, (0,0,255), 2)
            print (len (cn [i]))
            print (cv2.matchShapes (cn_compare, cn [i], 1, 0))
            print (cv2.matchShapes (cn [i], cn_compare, 1, 0))
            print (cv2.matchShapes (cn_compare , translate_coordinates (cn [i], get_min_coordinates (cn [i])), 1, 0))
            print (cv2.matchShapes (translate_coordinates (cn_compare , get_min_coordinates (cn_compare)), translate_coordinates (cn [i], get_min_coordinates (cn [i])), 1, 0))

            cv2.imshow ('test', img)
            k = cv2.waitKey ()
            if k == 113 or k == 1048576 + 113:
                sys.exit ()
            elif k == 27 or k == 1048576 + 27:
                return
            elif k == 1048672:
                break

def build_sequential_chain (cn):
    chain = np.ndarray (cn.shape, cn.dtype)
    x = cn [0][0][0]
    y = cn [0][0][1]
    
    for c in range (len (cn)):
        if c > 0:
            x = cn [c - 1][0][0]
            y = cn [c - 1][0][1]
            
        chain [c][0][0] = cn [c][0][0] - x
        chain [c][0][1] = cn [c][0][1] - y
        
        if chain [c][0][0] > 1:
            chain [c][0][0] = 1
        elif chain [c][0][0] < -1:
            chain [c][0][0] = -1
        if chain [c][0][1] > 1:
            chain [c][0][1] = 1
        elif chain [c][0][1] < -1:
            chain [c][0][1] = -1
        
    return chain

def chain_to_dispersion (chain):
    dispersion = []
    for c in chain:
        dispersion.append (spatial_dispersion [c [0][0], c [0][1]])

    return dispersion

def dispersion_normalize (d, recursive = False):
    recurse = []
    new_d = []
    for i in range (len (d)):
        if i < len (d) - 1:
            if d [i] == d [i+1]:
                continue
        if i < len (d) - 3:
            if d [i] == d [i+2] and d [i+1] == d [i+3]:
                continue
        
        new_d.append (d [i])
    if recursive:
        while not len (new_d) == len (recurse):
            recurse = new_d
            new_d = dispersion_normalize (new_d)
    return new_d

def dispersion_to_contour (dispersion, scale = 1):
    if isinstance (dispersion, str):
        if dispersion [0] in human_readable_codes_for_dispersion:
            dispersion = human_readable_to_dispersion (dispersion)
        
        l = list (dispersion)
        dispersion = []
        for a in l:
            dispersion.append (int (a))
    
    cn = np.ndarray ((len (dispersion), 1, 2), np.int32)
    cn.fill (0)
    x = y = 0
    counter = 0
    
    for d in dispersion:
        cn [counter][0] = x, y
        x += spatial_dispersion_r [d][0]
        y += spatial_dispersion_r [d][1]
        counter += 1
    
    x, y = get_min_coordinates (cn)
    if x < 0 or y < 0 or (x < 0 and y < 0):
        cn = translate_coordinates (cn, (x, y))
    if scale > 1:
        cn = cn * scale
    return cn

def human_readable_to_dispersion (code):
    translation = str ()
    for d in code:
        translation += str (human_readable_codes_for_dispersion [d])
    return translation

def dispersion_to_human_readable (dispersion):
    translation = str ()
    for d in dispersion:
        translation += human_readable_codes_for_dispersion [int (d)]
    return translation

def compare_contours_through_dispersionization (cn1, cn2):
    d1 = translate_coordinates (cn1, get_min_coordinates (cn1))
    chain1 = build_sequential_chain (d1)
    dispersion1 = chain_to_dispersion (chain1)
    dispersion1 = dispersion_normalize (dispersion1, recursive = True)
    cns1 = dispersion_to_contour (dispersion1)

    d2 = translate_coordinates (cn2, get_min_coordinates (cn2))
    chain2 = build_sequential_chain (d2)
    dispersion2 = chain_to_dispersion (chain2)
    dispersion2 = dispersion_normalize (dispersion2, recursive = True)
    cns2 = dispersion_to_contour (dispersion2)

    dd1 = contour_to_dispersion_hash (cn1)
    dd2 = contour_to_dispersion_hash (cn2)
    print (dd1, dd2)
    print (dispersion_to_hash (dispersion1), '\n', dispersion_to_hash (dispersion2))
    #return cns1, cns2
    return cv2.matchShapes (cns1, cns2, 1, 0)

def compare_dispersions (filename):
    im = cv2.imread (filename, -1)
    c = cv2.Canny (im, 100, 200)
    cv2.namedWindow('test')
    i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    img = np.ndarray (im.shape, dtype = im.dtype)
    img.fill (0)

    cn_comparison = copy.deepcopy (cn)
    cn.sort (key = len, reverse = True)
    cn_comparison.sort (key = len, reverse = True)
    
    for cn_compare in cn_comparison:
        for i in range (len (cn)):
            print ('{} of {}: {}'.format (i, len (cn) - 1, len (cn [i])))
            img.fill (0)
            cv2.drawContours (img, cn, -1, (150, 150,150), 1)
            cv2.drawContours (img, cn, i, (uniform (.7, 1) * 255, uniform (.7, 1) * 255, uniform (.7, 1) * 255), 2)
            cv2.drawContours (img, cn_compare, -1, (0,0,255), 2)
            print (cv2.matchShapes (cn_compare, cn [i], 1, 0))
            print (compare_contours_through_dispersionization (cn_compare, cn [i]))
            
            #cns1, cns2 = compare_contours_through_dispersionization (cn_compare, cn [i])
            #cv2.drawContours (img, cns1, -1, (255,0,255), 2)
            #cv2.drawContours (img, cns2, -1, (0,255,255), 2)
            #print (cv2.matchShapes (cns1, cns2, 1, 0))
            

            cv2.imshow ('test', img)
            k = cv2.waitKey ()
            if k == 113 or k == 1048576 + 113:
                sys.exit ()
            elif k == 27 or k == 1048576 + 27:
                return
            elif k == 1048672:
                break


def points_of_interest (filename):
    tolerance = 1
    im = cv2.imread (filename, -1)
    c = cv2.Canny (im, 100, 200)    
    i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cn.sort (key = len, reverse = True)
    cv2.namedWindow ('0')
    
    for contour in cn:
        d = translate_coordinates (contour, get_min_coordinates (contour))
        chain = build_sequential_chain (d)
        dispersion = chain_to_dispersion (chain)
        dispersion = dispersion_normalize (dispersion, recursive = True)
        print (dispersion)
        cns = dispersion_to_contour (dispersion)
        #print (cns)
        new = []
        
        im.fill (0)
        cv2.drawContours (im, cns, -1, (255, 255,255), 1)
        cv2.drawContours (im, contour, -1, (255, 255,255), 1)
        cv2.imshow ('0', im)
        
        k = cv2.waitKey ()
        if k == 113 or k == 1048576 + 113:
            sys.exit ()
        elif k == 27 or k == 1048576 + 27:
            return
        elif k == 1048672:
            break
        

        #new_cn = np.ndarray ((len (new), 1, 2), cn [0].dtype)
        
        #if len (new_cn) == 0:
            #continue
        
        #for c in range (len (new)):
            #new_cn [c][0][0] = new [c][0]
            #new_cn [c][0][1] = new [c][1]
        
        #print (new_cn, len (new_cn))
        #cv2.namedWindow('test')
        #im.fill (0)
        #cv2.drawContours (im, new_cn, -1, (255, 255,255), 4)
        #cv2.drawContours (im, contour, -1, (255, 255,255), 1)
        #cv2.imshow ('test', im)
        #key = cv2.waitKey ()
        #if key == 113:
            #sys.exit ()
    
def contour_pattern (filename):
    im = cv2.imread (filename, -1)
    c = cv2.Canny (im, 100, 200)    
    i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cn.sort (key = len, reverse = True)
    cv2.namedWindow ('0')
    
    for contour in cn:
        im.fill (0)
        d = translate_coordinates (contour, get_min_coordinates (contour))
        cv2.drawContours (im, d, -1, (255, 255,255), 1)
        cv2.imshow ('0', im)
        for i in range (len (d)):
            print (d [i])
        k = cv2.waitKey ()
        if k == 113 or k == 27:
            sys.exit ()

def dispersion_to_hash (dispersion):
    res = ''
    for d in dispersion:
        res += str (d)

    return res
    
def contour_to_dispersion_hash (value):
    d = translate_coordinates (value, get_min_coordinates (value))
    chain = build_sequential_chain (d)
    dispersion = chain_to_dispersion (chain)
    
    # this does not work, so we disable it
    #dispersion = dispersion_normalize (dispersion, recursive = True)
    dispersion = dispersion_to_human_readable (dispersion)

    res = ''
    for d in dispersion:
        res += str (d)

    return res

class ContourStorage (ZODBDataSource):
    # this is not the way to do it :(
    tolerance = 0.01 #10/3

    def __init__ (self, ui):
        self.ui = ui
        self.known_data_types = [str, Contour]
    
    def set (self, value, key):
        assert isinstance (value, Contour) and isinstance (key, str)
        self.open () if self.root is None else True
        
        #print (key, value)
        if isinstance (value, np.ndarray):
            value = contour_to_dispersion_hash (value)
        elif isinstance (value, Contour):
            value = str (value)
        
        if isinstance (key, np.ndarray):
            key = contour_to_dispersion_hash (key)
        elif isinstance (key, Contour):
            key = str (key)

        self.storage.link (["type", "str", key, "contour", value], ["type", "contour", value])
        self.storage.link (["type", "contour", value, "str", key], ["type", "str", key])
        self.storage.commit ()

    def get (self, key):
        self.open () if self.root is None else True

        if isinstance (key, str):
            types = self.storage.get ("type", str (type (key).__name__), str (key))
            if types is None:
                return None
            
            res = dict ()
            for i in types:
                res [i] = self.storage.get ("type", str (type (key).__name__), str (key), str (i), recursive = False)
            return res
        
        elif isinstance (key, np.ndarray):
            value = contour_to_dispersion_hash (key)
            if not self.storage.query ('type', 'contour', value):
                value = self.get_absolute_key (value)
                if value is None:
                    return None
            
            types = self.storage.get ("type", "contour", value)
            res = dict ()
            for i in types:
                res [i] = self.storage.get ("type", "contour", value, str (i), recursive = False)
            return res
        elif isinstance (key, Contour):
            value = str (key)
            if not self.storage.query ('type', 'contour', value):
                value = self.get_absolute_key (value)
                if value is None:
                    return None
            
            types = self.storage.get ("type", "contour", value)
            res = dict ()
            for i in types:
                res [i] = self.storage.get ("type", "contour", value, str (i), recursive = False)
            return res
        else:
            raise NotImplementedError

    def get_absolute_key (self, key):
        if isinstance (self.storage.root, persistent.mapping.PersistentMapping) and 'type' not in self.storage.root:
            return
        elif isinstance (self.storage.root, BTrees.OOBTree.OOBTree) and not self.storage.root.has_key ('type'):
            return
        #if not hasattr (self.storage.root, 'type') or hasattr (self.storage.root ['type'], 'contour'):
            #return None
        
        keys = []
        try:
            for i in self.storage.root ['type']['contour']:
                keys.append (i)
        except Exception as e:
            #print (e)
            self.ui.message ('An error occurred: ' + str (e), 'ui-error')
            return None
        
        if isinstance (key, np.ndarray):
            key = contour_to_dispersion_hash (key)
        elif isinstance (key, Contour):
            key = str (key)

        res = []
        for k in keys:
            s = SequenceMatcher (None, key, k)
            # real quick is fastest, but (relatively) least accurate
            # quick is faster, but (relatively) less accurate
            # ratio is (relatively) slowest, but most accurate
            # possible bottleneck, doesn't seem to be so now
            # but check here if performance becomes an issue
            #res.append ([s.real_quick_ratio (), k])
            #res.append ([s.quick_ratio (), k])
            res.append ([s.ratio (), k])
        
        res.sort ()
        if res [-1][0] > self.tolerance:
            return res [-1][1]
        else:
            return None
        #for counter in range (self.tolerance):
            #if key [counter:] in keys:
                #return key [counter:]
            #elif key [:-counter] in keys:
                #return key [:-counter]
            ##  Maybe add more here?
        return None
        

    def query (self, key):
        self.open () if self.root is None else True
        ab = self.get_absolute_key (key)
        if ab:
            return True
        else:
            return False


#if __name__ == '__main__':
    #compare_dispersions (sys.argv [1])
    #contour_pattern (sys.argv [1])
    #points_of_interest (sys.argv [1])
    #for filename in sys.argv [1:]:
        #do_contours (filename, filename)

    #if len (sys.argv) > 2:
        #for filename in sys.argv [2:]:
            #do_contours (sys.argv [1], filename)
    #else:
        #do_contours (sys.argv [1], sys.argv [1])

def copy_contour_multi_thread (mythread, thread_number):
    args = mythread.args
    cn = args ['contour']
    image = args ['image']
    x = args ['x']
    y = args ['y']
    maxx = args ['maxx']
    maxy = args ['maxy']
    minx = args ['minx']
    miny = args ['miny']
    
    res = np.ndarray ((maxy - miny, maxx - minx, 3), image.dtype)
    res.fill (0)
    start = int ((thread_number) * (len (cn) / mythread.threads))
    end = int ((thread_number + 1) * (len (cn) / mythread.threads))
    for b in x [start:end]:
        for a in y:
            if cv2.pointPolygonTest (cn, (b,a), False) > 0:
                try:
                    res [a - miny][b - minx] = image [a][b]
                except IndexError:
                    print (b, a, b - miny, a - minx, res.shape)
                    pass
    
    #print (len (x), len (y))
    mythread.queues [thread_number].put (res)

def copy_contour_multi (cn, image, threads = 4):
    args = dict ()
    args ['image'] = image
    args ['contour'] = cn

    x = []
    y = []
    
    for c in cn:
        x.append (c [0][0])
        y.append (c [0][1])
    
    minx = min (x)
    maxx = max (x)
    miny = min (y)
    maxy = max (y)

    args ['x'] = x
    args ['y'] = y
    args ['maxx'] = maxx
    args ['maxy'] = maxy
    args ['minx'] = minx
    args ['miny'] = miny

    mythread = Thread (threads, copy_contour_multi_thread, args)
    mythread.start ()
    mats = mythread.get_data ()
    mythread.join ()
    
    image = mats [0]
    for x in range (1, len (mats)):
        image += mats [x]
    #for x in range (1, len (mats)):
        #image += mats [x]
        #np.append (image, mats [x], axis = 1)
    
    return image

def copy_contour_rectangle (image, x, y, width, height):
    selection = np.ndarray (((height * 2), (width * 2), 3), np.int32)
    selection.fill (0)
    
    for b in range (height * 2):
        for a in range (width * 2):
            selection [b, a] = image [b + y, a + x]

    return selection


def contour_sort_func (a):
    #print (a [0][0], a [0][0][0])
    return a [0][0][0]

class ContourFocus:
    selection = None # []
    clusters = None # []
    center = -1
    canny1 = 100
    canny2 = 200
    
    class CannyModes (Enum):
        External = cv2.RETR_EXTERNAL
        List = cv2.RETR_LIST
        Comp = cv2.RETR_CCOMP
        Tree = cv2.RETR_TREE
    
    class CannyMethods (Enum):
        none = cv2.CHAIN_APPROX_NONE
        Simple = cv2.CHAIN_APPROX_SIMPLE
        TC89 = cv2.CHAIN_APPROX_TC89_L1
        TC_KC = cv2.CHAIN_APPROX_TC89_KCOS
    
    mode = cv2.RETR_EXTERNAL
    method = cv2.CHAIN_APPROX_NONE
    
    draw_all_contours = True
    draw_only_contours = False
    randomize = True
    colors = []
    center = [50,50]
    colors_range = (150, 255)
    thickness = 1
    selection_color = 0, 0, 255
    es_color = 17, 151, 255
    tolerance = 70
    proximity_tolerance = 100 # px
    flip = False
    flip_axis = 1
    
    def select_cluster (self, cluster):
        if self.clusters is None or cluster is None:
            return
        
        if len (self.clusters) > cluster:
            self.selection = self.clusters [cluster]
            #cn = self.get (self.ui.current_frame, raw = True, current = False)    
            cn = self.get (self.ui.current_frame, raw = True, current = False, multi = True, es = self.ui.focus_mode.value == 3 or self.ui.focus_mode.value == 5)
            #print (cn [self.selection [0]])
            #self.center [0] = cn [self.selection [0]][0][0][0]
            #self.center [1] = cn [self.selection [0]][0][0][1]
            #print (self.center)
            self.center = [cn [self.selection [0]][0][0][0], cn [self.selection [0]][0][0][1]]
        else:
            warn (debug_info () + 'self.clusters is empty')

    def append_selection_to_clusters (self):
        self.clusters.append (self.selection)
    
    def selection_to_clusters (self):
        self.clusters_clear ()
        self.append_selection_to_clusters ()

    def match_color (self, color1, color2, tolerance = -1):
        if tolerance == -1:
            tolerance = self.tolerance
        if abs (color1 [0] - color2 [0]) < tolerance and abs (color1 [1] - color2 [1]) < tolerance and abs (color1 [2] - color2 [2]) < tolerance:
            return True
        else:
            return False

    def match_proximity (self, cn1, cn2, tolerance = -1):
        if tolerance == -1:
            tolerance = self.proximity_tolerance
        
        min_x1, min_y1 = cn1.min (0)[0]
        max_x1, max_y1 = cn1.max (0)[0]
        min_x2, min_y2 = cn2.min (0)[0]
        max_x2, max_y2 = cn2.max (0)[0]
        
        list1 = (min_x1, min_y1), (max_x1, min_y1), \
                (min_x1, max_y1), (max_x1, max_y1)

        list2 = (min_x2, min_y2), (max_x2, min_y2), \
                (min_x2, max_y2), (max_x2, max_y2)
    
        for a in list1:
            for b in list2:
                if abs (a [0] - b [0]) < tolerance and abs (a [1] - b [1]) < tolerance:
                    return True
        return False

    def selection_auto_select_cluster (self, generate_clusters = False):
        if generate_clusters:
            self.selection_auto_select_generated_cluster ()
            return
        
        cn = self.ui.get_focus (raw = True, multi = False, current = False)
        if not isinstance (cn, list) or not len (cn) > 0: #isinstance (cn, np.ndarray) or not cn.shape [2] == 2:
            warn (str (type (cn)))
            #warn (str (cn))
            return None

        frame = self.ui.get_frame ()
        selection = cn [self.selection [0]]
        
        color1 = contour_get_mean_color (frame, selection, return_type = tuple)
        
        for c in range (len (cn)):
            if c in self.selection:
                continue
            
            if self.match_proximity (selection, cn [c]):
                color2 = contour_get_mean_color (frame, cn [c], return_type = tuple)
                if color1 is None or color2 is None:
                    continue
                
                if self.match_color (color1, color2):
                    self.selection.append (c)
                    

    def selection_auto_select_generated_cluster (self):
        cn = self.ui.get_focus (raw = True, multi = False, current = False)
        if not isinstance (cn, list) or not len (cn) > 0: #isinstance (cn, np.ndarray) or not cn.shape [2] == 2:
            warn (str (type (cn)))
            #warn (str (cn))
            return None

        clusters = self.ui.get_focus (focus_mode = 6, raw = True, multi = True, clusters = True)
        if clusters is None or cn is None:
            return None
        
        #print (cn [3][0])
        #sys.exit ()

        if not isinstance (clusters, list) or not len (cn) > 0:
            warn (clusters)
            return None
        
        frame = self.ui.get_frame ()
        color1 = contour_get_mean_color (frame, cn [self.selection [0]], return_type = tuple)
        
        for cluster in clusters:
            for c in cluster:
                color2 = contour_get_mean_color (frame, cn [c], return_type = tuple)
                if self.match_proximity (cn [c], cn [self.selection [0]]) and self.match_color (color1, color2):
                    for u in cluster:
                        self.selection.append (u)
                    return

    def generate_contour_clusters1 (self):
        self.ui.timer.reset ()
        cn = self.get (self.ui.current_frame, raw = True, current = False, multi = True, es = self.ui.focus_mode.value == 3 or self.ui.focus_mode.value == 5)
        self.clusters = []
        match_found = False
        #print (len (cn))
        self.ui.progress_set (0, 'generating contours...')
        #update_interval = 2
        #update_counter = 0
        
        for c in range (len (cn)):
            #print (c)
            
            #if update_counter > update_interval:
                #update_counter = 0
            if self.ui.abort.get_active ():
                break
            self.ui.progress_set (c / len (cn), 'generating contours... {}/{}'.format (c, len (cn)))
            self.ui.update_ui ()
            #else:
                #update_counter += 1
            
            match_found = False
            if not len (self.clusters):
                self.clusters.append ([c])
            
            if len (cn [c]) < 500:
                color1 = contour_get_mean_color (self.ui.current_frame, cn [c], return_type = tuple)
            else:
                color1 = contour_get_mean_color_multi (self.ui.current_frame, cn [c], return_type = tuple)
            for i in self.clusters:
                if len (cn [i [0]]) < 400:
                    color2 = contour_get_mean_color (self.ui.current_frame, cn [i [0]], return_type = tuple)
                else:
                    color2 = contour_get_mean_color_multi (self.ui.current_frame, cn [i [0]], return_type = tuple)
            
                if color1 is None or color2 is None:
                    continue
                if self.match_color (color1, color2, self.tolerance) and self.match_proximity (cn [c], cn [i [0]]):
                    match_found = True
                    i.append (c)
                    #print ('1: ', color1, color2)
                    break
            if not match_found:
                #print ('0: ', color1, color2)
                self.clusters.append ([c])
        self.ui.progress_reset ()
        self.ui.message ('Generated {} clusters in {} seconds'.format (len (self.clusters), self.ui.timer.time ()), 'input')
        return self.clusters
    
    def generate_contour_clusters (self):
        self.ui.timer.reset ()
        cn = self.get (self.ui.current_frame, raw = True, current = False, multi = True, es = self.ui.focus_mode.value == 3 or self.ui.focus_mode.value == 5)
        self.clusters = []
        match_found = False
        #print (len (cn))
        self.ui.progress_set (0, 'generating contours...')
        self.ui.update_ui ()
        
        colors = []
        clusters = []

        data = []
        for i in cn:
            data.append ((self.ui.current_frame, i, tuple))

        colors = self.ui.manager.submit_job (contour_get_mean_color_callback, data)
        #pool = multiprocessing.Pool ()
        #colors = pool.map (contour_get_mean_color_callback, data)
        
        #for i in range (len (cn)):
            #c = cn [i]
            #if len (c) < 500:
                #color = contour_get_mean_color (self.ui.current_frame, c, return_type = tuple)
            #else:
                #color = contour_get_mean_color_multi (self.ui.current_frame, c, return_type = tuple)
            #if self.ui.abort.get_active ():
                #break

            #self.ui.progress_set (i / len (cn), 'generating contours... {}/{}'.format (i, len (cn)))
            #self.ui.update_ui ()

            #colors.append (color)
        
        update_interval = 10
        update_counter = 0
        
        for c in range (len (cn)):
            if update_counter > update_interval:
                update_counter = 0
                if self.ui.abort.get_active ():
                    break
                self.ui.progress_set (c / len (cn), 'generating contours... {}/{}'.format (c, len (cn)))
                self.ui.update_ui ()
            else:
                update_counter += 1
            
            match_found = False
            if not len (self.clusters):
                clusters.append ([[c], colors [c]])
                #continue
            
            color1 = colors [c]
            for i in clusters:
                #print(i)
                color2 = i [1]
                if color1 is None or color2 is None:
                    #continue
                    break
                if self.match_color (color1, color2, self.tolerance) and self.match_proximity (cn [c], cn [i[0][0]]):
                    match_found = True
                    i [0].append (c)
                    #print ('1: ', color1, color2)
                    break
            if not match_found:
                #print ('0: ', color1, color2)
                clusters.append ([[c], color2])
        self.ui.progress_reset ()
        
        self.clusters = []
        for c in clusters:
            #print (c[0])
            if len (c [0]) > 1:
                self.clusters.append (c [0])

        self.ui.message ('Generated {} clusters in {} seconds'.format (len (self.clusters), self.ui.timer.time ()), 'input')
        #self.clusters.sort (key = len, reverse = True)
        return self.clusters

    def clusters_clear (self):
        self.clusters = []
        
    # i know, i know, but i didn't know when i wrote it
    # i just don't have the heart to delete it now

    def getattr (self, attribute):
        if hasattr (self, attribute):
            return getattr (self, attribute)
        else:
            raise AttributeError
    
    def setattr (self, attribute, value):
        setattr (self, attribute, value)

    def set_ (self, canny1 = 0, canny2 = 0, draw_all_contours = None, 
             draw_only_contours = None, randomize = None):
        raise RuntimeError
        
        if canny1:
            self.canny1 = canny1
            
        if canny2:
            self.canny2 = canny2
    
        if isinstance (draw_all_contours, bool):
            self.draw_all_contours = draw_all_contours

        if isinstance (randomize, bool):
            self.randomize = randomize

        if isinstance (draw_only_contours, bool):
            self.draw_only_contours = draw_only_contours

    def select_all (self, cn):
        self.selection = []
        for i in range (len (cn)):
            self.selection.append (i)
    
    def select_range (self, cn, start, end):
        self.selection = []
        for i in range (start, end):
            self.selection.append (i)
    
    def append_contour_to_selection_at_coords (self, cn, coords):
        for i in range (len (cn)):
            c = cn [i]
            test = cv2.pointPolygonTest (c, (coords [0], coords [1]), False)
            if test >= 0:
                #self.selection = np.append (self.selection + c, 0)
                self.selection.append (i)
                break
        
    
    def __init__ (self, ui = None):
        self.canny1 = 100
        self.canny2 = 200
        if ui:
            self.ui = ui
            # this is important :0
            self.center = self.ui.colorfocus.center
        
        self.selection = []
        self.clusters = []
    
    def draw (self, image, es = False):
        #print (self.canny1, self.canny2)

        if es:
            center, side = self.ui.get_focus_coords ('color')
            x = center [0] - side [0]
            y = center [1] - side [1]
            x2 = center [0] + side [0]
            y2 = center [1] + side [1]
            selection = copy_contour_rectangle (image, x, y, side [0], side [1]).astype (np.uint8)
            #self.ui.peep (selection)
            c = cv2.Canny (selection, self.canny1, self.canny2)    
            i, cn, hr = cv2.findContours (c, self.mode, self.method)
            cn = translate_coordinates (cn, (x,y), reverse = True)
            image = cv2.rectangle (image, (x,y), (x2,y2), self.es_color, self.thickness if self.thickness > 0 else abs (self.thickness))
            image = cv2.circle (image, (self.center [0], self.center[1]), 7, self.es_color, self.thickness if self.thickness > 0 else abs (self.thickness))
        else:
            c = cv2.Canny (image, self.canny1, self.canny2)    
            i, cn, hr = cv2.findContours (c, self.mode, self.method)
            image = cv2.circle (image, (self.center [0], self.center[1]), 7, self.selection_color, self.thickness + 1)
        
        cn.sort (key = len, reverse = True)
        #cn.sort (key = contour_sort_func, reverse = False)
        
        #sub = np.ndarray ((3,), image.dtype)
        #sub.fill (2)
        #image = image + sub
        #image = np.floor_divide (image, sub)
        #image = cv2.blur (image, (5,5))
        
        #color = (255,255,255)
        
        #if self.randomize:
            #color = (randrange (100, 255),
                    #randrange (100, 255),
                    #randrange (100, 255))
        
        if self.draw_only_contours:
            image.fill (0)
        
        if self.draw_all_contours:
            if self.randomize:
                if len (self.colors) < len (cn):
                    self.colors = []
                    for c in cn:
                        self.colors.append ((randrange (100, 255), randrange (100, 255), randrange (self.colors_range [0], self.colors_range [1])))
                for i in range (len (cn)):
                    cv2.drawContours (image, cn, i, self.colors [i], self.thickness)
            else:
                cv2.drawContours (image, cn, -1, (255,255,255), self.thickness)
                #cv2.drawContours (image, cn, -1, self.selection_color, self.thickness)
        
        #if self.center == -1:
            #cv2.drawContours (image, cn, self.selection, self.selection_color, self.thickness + 1 if self.thickness > 0 else abs (self.thickness))
        #elif es:
            #cv2.drawContours (image, cn, 0, (0, 0, 255), self.thickness + 1)

        # this is where the selection is drawn
        if not es and len (self.selection) and self.selection [0] < len (cn) and cv2.pointPolygonTest (cn [self.selection [0]], (self.center [0], self.center [1]), False) >= 0:
            contour = cn [self.selection [0]]
            for i in range (1, len (self.selection)):
                contour = np.append (contour, cn [self.selection [i]], 0)
            cv2.drawContours (image, contour, -1, self.selection_color, self.thickness + 1 if self.thickness > 0 else abs (self.thickness))
            if self.thickness < 0:
                image = cv2.drawContours (image, [contour], -1, self.selection_color, -1)
                #print ('aye')
            #for s in self.selection:
                #cv2.drawContours (image, cn, s, self.selection_color, self.thickness + 1 if self.thickness > 0 else abs (self.thickness))
        elif es and len (self.selection) and self.selection [0] < len (cn) and cv2.pointPolygonTest (cn [self.selection [0]], (self.center [0], self.center [1]), False) >= 0:
            contour = cn [self.selection [0]]
            for i in range (1, len (self.selection)):
                if self.selection [i] < len (cn):
                    contour = np.append (contour, cn [self.selection [i]], 0)
            cv2.drawContours (image, contour, -1, self.selection_color, self.thickness + 1 if self.thickness > 0 else abs (self.thickness))
            if self.thickness < 0:
                image = cv2.drawContours (image, [contour], -1, self.selection_color, -1)
        else:
            self.selection = []
            for i in range (len (cn)):
                c = cn [i]
                test = cv2.pointPolygonTest (c, (self.center [0], self.center [1]), False)
                if test >= 0:
                    cv2.drawContours (image, c, -1, self.selection_color, self.thickness + 1 if self.thickness > 0 else abs (self.thickness))
                    self.selection.append (i)
                    #break
        if self.flip:
            image = cv2.flip (image, self.flip_axis)

        return image

    def get (self, image, raw = False, es = False, current = True, multi = False):
        assert (isinstance (image, np.ndarray)) and image.shape [2] == 3

        if es:
            center, side = self.ui.get_focus_coords ('color')
            x = center [0] - side [0]
            y = center [1] - side [1]
            selection = copy_contour_rectangle (image, x, y, side [0], side [1]).astype (np.uint8)
            #self.ui.peep (selection)
            c = cv2.Canny (selection, self.canny1, self.canny2)    
            i, cn, hr = cv2.findContours (c, self.mode, self.method)
            cn = translate_coordinates (cn, (x,y), reverse = True)
        else:
            c = cv2.Canny (image, self.canny1, self.canny2)    
            i, cn, hr = cv2.findContours (c, self.mode, self.method)

        cn.sort (key = len, reverse = True)
        
        current_index = 0
        
        #if self.selection [0] < len (cn):
            #current_index = self.selection [0]
        
        #for i in range (len (cn)):
            #c = cn [i]
            #test = cv2.pointPolygonTest (c, tuple (self.center), False)
            #if test >= 0:
                #current_index = i
                #break
        
        if current:
            # uncomment this if this throws an exception
            if multi:
                contour = []
                for i in self.selection:
                    contour.append (cn [i])
                cn = contour
            else:
                contour = None
                if len (self.selection) and self.selection [0] < len (cn) and cv2.pointPolygonTest (cn [self.selection [0]], (self.center [0], self.center [1]), False) >= 0:
                    contour = cn [self.selection [0]]
                    for i in range (1, len (self.selection)):
                        contour = np.append (contour, cn [self.selection [i]], 0)
                else:
                    return None
                cn = contour
        if raw:
            return cn
        else:
            #image = copy_contour_multi (cn, image)
            bg = contour_get_mean_color_multi (image, cn, return_type = tuple)
            if bg is None:
                #print (cn)
                warn (debug_info () + ' returned None!')
                bg = 0, 0, 0
                fg = 255, 255, 255
            else:
                fg = bg [0] + 50, bg [1] + 50, bg [2] + 50
            #print (fg, bg)
            image = generate_image_from_contour (cn, bg = bg, fg = fg)
            return image

        # unused
        #
        #x = []
        #y = []
        
        #for c in cn:
            #x.append (c [0][0])
            #y.append (c [0][1])
        
        #minx = min (x)
        #maxx = max (x)
        #miny = min (y)
        #maxy = max (y)
        
        #res = np.ndarray ((maxy - miny, maxx - minx, 3), image.dtype)
        #res.fill (0)
        #for b in x:
            #for a in y:
                #if cv2.pointPolygonTest (cn, (b,a), False) > 0:
                    #try:
                        #res [a - miny][b - minx] = image [a][b]
                    #except IndexError:
                        #print (b, a, b - miny, a - minx, res.shape)
        #return res


class Contour:
    dispersion = None
    def __init__ (self, dispersion):
        self.__repr__ = self.__str__
        self.dispersion = dispersion
    
    def __str__ (self):
        #print (self.dispersion)
        return self.dispersion

class ContourInput (Input):
    def get_preview (self, cn, size = -1):
        if size == -1:
            size = self.ui.PREVIEW_ICON_SIZE
        
        return generate_image_from_contour (dispersion_to_contour (str (cn), scale = 5))

    def poll (self):
        # direct raw access to focus internal data
        # i.e contours
        cn = self.ui.get_focus (raw = True)
        if cn is None:
            return None
        elif isinstance (cn, np.ndarray) and cn.shape [2] == 2:
            dispersion = contour_to_dispersion_hash (cn)
            return Contour (dispersion)
        return None
        
        #image = self.ui.get_focus () #focus_mode = 2)
        #if image is None:
            #return None
        
        image = cn    
        c = None
        try:
            c = cv2.Canny (image, 100, 200)    
        except cv2.error as e:
            self.ui.message (str (e), 'input-error')
            try:
                cf = ContourFocus ()
                image = cf.get (image)
                c = cv2.Canny (image, 100, 200)
            except cv2.error as e:
                self.ui.message (str (e), 'input-error')
                return None

        i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cn.sort (key = len, reverse = True)

        #d = translate_coordinates (cn [0], get_min_coordinates (cn [0]))
        #chain = build_sequential_chain (d)
        #dispersion = chain_to_dispersion (chain)
        #dispersion = dispersion_normalize (dispersion, recursive = True)
        
        dispersion = contour_to_dispersion_hash (cn [0])
        return Contour (dispersion)

def contour_frame_get_mean_color (image, cn, return_type = str):
    blue = green = red = 0
    counter = 0
    
    for c in cn:
        blue += image [c [0][1], c [0][0]][0]
        green += image [c [0][1], c [0][0]][0]
        red += image [c [0][1], c [0][0]][0]
        counter += 1

    blue = blue / counter
    green = green / counter
    red = red / counter
    
    if return_type is tuple:
        return int (blue), int (green), int (red)
    elif return_type is str or return_type is Color:
        #c = get_mean_color_multi (image)
        #tt = (int (c [2]) / 255, int (c[1]) / 255, int (c[0]) / 255)
        tt = red / 255, green / 255, blue / 255
        c = Color (rgb = tt)
        if return_type is Color:
            return c
        else:
            return str (c)
    else:
        return None
        
def generate_image_from_contour (cn, fg = None, bg = None):
    #print (cn.min (0))
    padding = 10
    if fg is None:
        fg = 0, 0, 0
    
    if bg is None:
        bg = 255, 255, 255
    
    min_x = min_y = max_x = max_y = 0
    
    if isinstance (cn, list):
        if len (cn) is 0:
            return None
        
        lminx = []
        lminy = []
        lmaxx = []
        lmaxy = []
        
        for c in cn:
            min_x, min_y = c.min (0)[0]
            max_x, max_y = c.max (0)[0]
            lminx.append (min_x)
            lminy.append (min_y)
            lmaxx.append (max_x)
            lmaxy.append (max_y)
        min_x = min (lminx)
        min_y = min (lminy)
        max_x = max (lmaxx)
        max_y = max (lmaxy)
    else:
        min_x, min_y = cn.min (0)[0]
        max_x, max_y = cn.max (0)[0]
    
    image = np.ndarray ((max_y - min_y + padding * 2, max_x - min_x + padding * 2, 3), dtype = np.uint8)
    image.fill (255)
    image [:] = bg
    cn = translate_coordinates (cn, (min_x - padding, min_y - padding))
    cv2.drawContours (image, cn, -1, fg, 3)
    return image

class ContourCluster:
    dispersions = None # []
    def __init__ (self, dispersions):
        self.__repr__ = self.__str__
        self.dispersions = dispersions
    
    def __str__ (self):
        #print (self.dispersion)
        return 'ContourCluster: {}'.format (self.dispersions)

    def get (self):
        return self.dispersions
    
    # heh
    def __len__ (self):
        return len (self.dispersions) if self.dispersions is not None else 0

class ContourClusterInput (Input):
    def poll (self):
        cn = self.ui.get_focus (raw = True, multi = True)
        image = self.ui.get_frame ()
        if cn is None:
            return None
        #elif not isinstance (cn, np.ndarray) and cn.shape [2] == 2:
        elif not isinstance (cn, list) or not len (cn) > 0:
            #warn ('{} of length {} passed!'.format (type (cn), len (cn)))
            return None
            #raise TypeError
        elif not isinstance (cn [0], np.ndarray):
            #warn ('list of {} returned!'.format (type (cn [0])))
            return None
        
        dispersions = []
        for c in cn:
            #print (c)
            dispersion = contour_to_dispersion_hash (c)
            dispersions.append (dispersion)

        return ContourCluster (dispersions)

class AutoContourClusterInput (Input):
    def get_preview1 (self, contour_cluster, size = -1):
        if size == -1:
            size = self.ui.PREVIEW_ICON_SIZE
        
        return generate_image_from_contour (contour_cluster.get ())

    def poll (self):
        cn = self.ui.get_focus (raw = True, multi = False, current = False)
        if not isinstance (cn, list) or not len (cn) > 0: #isinstance (cn, np.ndarray) or not cn.shape [2] == 2:
            warn (str (type (cn)))
            #warn (str (cn))
            return None

        clusters = self.ui.get_focus (focus_mode = 6, raw = True, multi = True, clusters = True)
        if clusters is None or cn is None:
            return None
        
        #print (cn [3][0])
        #sys.exit ()

        if not isinstance (clusters, list) or not len (cn) > 0:
            warn (clusters)
            return None

        x, y = self.ui.get_focus_coords (6)
        image = self.ui.get_frame ()

        for cluster in clusters:
            #count = 0
            #for u in cluster:
                #count += len (cn [cluster [u]])

            #contour = np.ndarray ((0, 1, 2), dtype = cn [0].dtype)
            #contour.fill (0)
            
            #milestone
            match = False
            for c in cluster:
                if cv2.pointPolygonTest (cn [c], (x, y), False) >= 0:
                    match = True
                    break
            
            if match:
                dispersions = []
                for c in cluster:
                    #print (c)
                    dispersion = contour_to_dispersion_hash (cn [c])
                    dispersions.append (dispersion)
        
                return ContourCluster (dispersions)
        return None
            
            #contour = cn [cluster [0]]
            #for u in range (1, len (cluster)):
                ##print (cn [cluster [u]])
                #contour = np.append (contour, cn [cluster [u]], 0)

            ##print (contour)
            ##if clusters.index (cluster) == 8:
                ##for c in contour:
            #print (cv2.pointPolygonTest (contour, (x, y), True))
            #print (x, y, clusters.index (cluster))
            
            #if cv2.pointPolygonTest (contour, (x, y), False) >= 0:
                #print ('yea')
                #dispersions = []
                #for d in c:
                    #dispersion = contour_to_dispersion_hash (d)
                    #dispersions.append (dispersion)
        
                #return ContourCluster (dispersions)
        #return None            

    def poll1 (self):
        cn = self.ui.get_focus (raw = True, multi = False, current = False)
        if not isinstance (cn, list) or not len (cn) > 0: #isinstance (cn, np.ndarray) or not cn.shape [2] == 2:
            warn (str (type (cn)))
            #warn (str (cn))
            return None

        clusters = self.ui.get_focus (focus_mode = 6, raw = True, multi = True, clusters = True)
        if clusters is None or cn is None:
            return None
        
        #print (cn [3][0])
        #sys.exit ()

        if not isinstance (clusters, list) or not len (cn) > 0:
            warn (clusters)
            return None

        x, y = self.ui.get_focus_coords (6)
        image = self.ui.get_frame ()

        for cluster in clusters:
            contour = cn [cluster [0]]
            for u in range (1, len (cluster)):
                contour = np.append (contour, cn [cluster [u]], 0)

            #print (cv2.pointPolygonTest (contour, (x, y), True))
            print (x, y, clusters.index (cluster))
            
            if cv2.pointPolygonTest (contour, (x, y), False) >= 0:
                dispersions = []
                for c in cluster:
                    #print (c)
                    dispersion = contour_to_dispersion_hash (cn [c])
                    dispersions.append (dispersion)
        
                return ContourCluster (dispersions)
        return None            

class ContourClusterStorage (ContourStorage):
    def __init__ (self, ui):
        self.ui = ui
        self.known_data_types = [str, ContourCluster]
    
    def set (self, value, key):
        assert isinstance (value, ContourCluster) and isinstance (key, str)
        self.open () if self.root is None else True
        
        for dispersion in value.dispersions:
            self.storage.link (['type', 'contour', str (dispersion), 'contourcluster', key], ['type', 'contourcluster', key])
            self.storage.link (["type", "contourcluster", key, "contour", str (dispersion)], ["type", "contour", str (dispersion)])
        
        self.storage.commit ()

    def get (self, cluster):
        self.open () if self.root is None else True
        if isinstance (cluster, str):
            dispersions = self.storage.get ("type", "contourcluster", cluster, "contour")
            return ContourCluster (dispersions)
        elif isinstance (cluster, ContourCluster):
            contours = []
            for dispersion in cluster.dispersions:
                if not self.storage.query ('type', 'contour', dispersion):
                    dispersion = self.get_absolute_key (dispersion)
                    if dispersion is None:
                        continue
                
                clusters = self.storage.get ('type', 'contour', str (dispersion), 'contourcluster')
                if clusters:
                    contours.append (clusters)
            
            if not len (contours):
                return None
            
            base = contours [0]
            counter = 0
            #print (contours)
            # justifyyy !!
            # contours = [['ball', 'bat'], ['ball', 'cat']]
            
            # this is flawed logic
            #if len (contours) == 1:
                #return base [0]
            #print (contours, cluster, clusters)

            for i in range (len (contours)):
                base = contours [i]
                
                for b in base:
                    matches = 0
                    for j in range (len (contours)):
                        # not excluding the list we are comapring
                        # because we want to include all the cases
                        #if i == j:
                            #continue
                        
                        if b in contours [j]:
                            matches += 1
                    #print (matches, b, contours, matches / len (contours))
                    #if matches / len (contours) > self.tolerance:
                    #print (matches, len (cluster))
                    if matches / len (cluster) > self.tolerance:
                        matched_cluster = self.storage.get ('type', 'contourcluster', b, 'contour')
                        #print (matches / len (matched_cluster))
                        if matched_cluster and matches / len (matched_cluster) > self.tolerance:
                            #print (matches, len (matched_cluster))
                            return b
            return None

    def query (self, cluster):
        if not isinstance (cluster, ContourCluster):
            #print ('contourcluster query: ' + cluster)
            return False

        #print ('contourcluster query: ' + str (cluster))
        
        self.open () if self.root is None else True
        # old way
        #a = self.get (cluster)
        #print (a)
        #if a:
            #return True
        #else:
            #return False
        # end old way
        contours = []
        for dispersion in cluster.dispersions:
            if not self.storage.query ('type', 'contour', dispersion):
                dispersion = self.get_absolute_key (dispersion)
                if dispersion is None:
                    continue
            
            clusters = self.storage.get ('type', 'contour', str (dispersion), 'contourcluster')
            if clusters:
                contours.append (clusters)
        
        if not len (contours):
            return False
        if len (contours) / len (cluster) < self.tolerance:
            #print (len (contours), len (cluster))
            return False
        else:
            #print ('True',len (contours), len (cluster))
            return True

def contour_get_mean_color (image, cn, return_type = str):
    warn ('legacy function', FutureWarning) #DeprecationWarning) #~ FutureWarning
    #return contour_get_mean_color_multi (image, cn, return_type)
    
    blue = green = red = 0
    counter = 0
    
    # update: we now use the cv2.mean function
    # which is (presumably) faster

    if isinstance (cn, list):
        for c in cn:
            bgr = contour_get_mean_color (image, c, return_type = tuple)
            if bgr is None:
                warn ('contour_get_mean_color returned None')
                continue
            
            blue += bgr [0]
            green += bgr [1]
            red += bgr [2]
            counter += 1
        
        blue = blue / counter
        green = green / counter
        red = red / counter
        
        if return_type is tuple:
            return int (blue), int (green), int (red)
        elif return_type is str or return_type is Color:
            tt = (red / 255, green / 255, blue / 255)
            c = Color (rgb = tt)
            if return_type is Color:
                return c
            else:
                return str (c)
        else:
            return None


    shape = copy_contour_multi (cn, image)
    blue, green, red, what_is_this = cv2.mean (shape, None)
    
    #min_x, min_y = cn.min (0)[0]
    #max_x, max_y = cn.max (0)[0]

    #for x in range (min_x, max_x):
        #for y in range (min_y, max_y):
            #if cv2.pointPolygonTest (cn, (x, y), False) >= 0:
                #blue += image [y, x][0]
                #green += image [y, x][1]
                #red += image [y, x][2]
                #counter += 1

    #if counter == 0:
        #return None
    
    #blue = blue / counter
    #green = green / counter
    #red = red / counter
    #print (blue, green, red, counter)
    if return_type is tuple:
        return int (blue), int (green), int (red)
    elif return_type is str or return_type is Color:
        # boys and girls, this is what you get when you copy/paste
        # stuff at 3 am.
        # lulz
        #c = get_mean_color_multi (image)
        tt = (red / 255, green / 255, blue / 255)
        c = Color (rgb = tt)
        if return_type is Color:
            return c
        else:
            return str (c)
    else:
        return None
        
def contour_get_mean_color_multi_thread (thread, thread_number):
    cn = thread.args ['cn']
    image = thread.args ['image']
    min_x = thread.args ['min_x']
    min_y = thread.args ['min_y']
    max_x = thread.args ['max_x']
    max_y = thread.args ['max_y']

    #print (min_x, min_y, max_x, max_y)

    blue = green = red = 0
    counter = 0
    difference = max_x - min_x
    difference = int (difference / thread.threads)
    #for x in range (min_x + (difference * thread_number), max_x - (difference * (thread.threads - thread_number))):
    for x in range (min_x + (difference * thread_number), (min_x + (difference * (thread_number + 1)))):
        for y in range (min_y, max_y):
            if cv2.pointPolygonTest (cn, (x, y), False) >= 0:
                blue += image [y, x][0]
                green += image [y, x][1]
                red += image [y, x][2]
                counter += 1
    
    if counter == 0:
        thread.queues [thread_number] .put (None)
        return

    blue = blue / counter
    green = green / counter
    red = red / counter
    
    thread.queues [thread_number] .put ([int (blue), int (green), int (red)])

def contour_get_mean_color_multi (image, cn, return_type = str):
    blue = green = red = 0
    counter = 0
    
    if isinstance (cn, list):
        for c in cn:
            bgr = contour_get_mean_color_multi (image, c, return_type = tuple)
            if bgr is None:
                warn ('contour_get_mean_color returned None')
                continue
            
            blue += bgr [0]
            green += bgr [1]
            red += bgr [2]
            counter += 1
        
        if counter == 0:
            return None
        
        blue = blue / counter
        green = green / counter
        red = red / counter
        
        if return_type is tuple:
            return int (blue), int (green), int (red)
        elif return_type is str or return_type is Color:
            tt = (red / 255, green / 255, blue / 255)
            c = Color (rgb = tt)
            if return_type is Color:
                return c
            else:
                return str (c)
        else:
            return None

    min_x, min_y = cn.min (0)[0]
    max_x, max_y = cn.max (0)[0]

    #print (min_x, min_y, max_x, max_y)

    args = {
        'image': image,
        'cn': cn,
        'min_x':min_x,
        'min_y': min_y,
        'max_x': max_x,
        'max_y': max_y
    }

    red = green = blue = 0
    number_of_threads = os.cpu_count ()
    thread = Thread (number_of_threads, contour_get_mean_color_multi_thread, args)

    thread.start ()
    data = thread.get_data ()
    thread.join ()
    #print (data)
    
    for i in data:
        if i is not None:
            blue += i [0]
            green += i [1]
            red += i [2]
    
    blue = int (blue / number_of_threads)
    green = int (green / number_of_threads)
    red = int (red / number_of_threads)

    if return_type is tuple:
        return int (blue), int (green), int (red)
    elif return_type is str or return_type is Color:
        tt = (red / 255, green / 255, blue / 255)
        c = Color (rgb = tt)
        if return_type is Color:
            return c
        else:
            return str (c)
    else:
        return None

def contour_get_mean_color_callback (data):
    return contour_get_mean_color (data [0], data [1], data [2])

def generate_lines ():
    image = np.ndarray ((400,400,3),dtype=np.uint8)
    image.fill (0)
    
    x = 200
    y = 100
    points  = []
    for z in range (100):
        points.append ((x - z, y + z))
    x = 100
    y = 200
    for z in range (100):
        points.append ((x - z, y - z))
    x = 0
    y = 100
    for z in range (100):
        points.append ((x + z, y - z))
    x = 100
    y = 0
    for z in range (100):
        points.append ((x + z, y + z))
    
    contours = []
    for p in points:
        image.fill (0)
        if p [0] > 100 and p [1] > 100:
            cv2.line (image, (100,100), p, (0,0,255), 1, cv2.LINE_AA)
        else:
            cv2.line (image, p, (100,100), (0,0,255), 1, cv2.LINE_AA)
        c = cv2.Canny (image, 200, 400)
        i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        dispersion = contour_to_dispersion_hash (cn [0])
        if dispersion not in contours:
            contours.append (dispersion)
    
    return contours

def generate_rectangles ():
    image = np.ndarray ((400,400,3), dtype = np.uint8)
    image.fill (0)
    cv2.rectangle (image, (100,100), (200,200), (255,255,255), 2, cv2.LINE_AA)
    
    contours = []
    for x in range (360):
        matrix = cv2.getRotationMatrix2D ((200, 200), x ,1)
        image2 = cv2.warpAffine (image, matrix, (400, 400))
        c = cv2.Canny (image2, 200, 400)
        i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        dispersion = contour_to_dispersion_hash (cn [0])
        if dispersion not in contours:
            contours.append (dispersion)
        
    return contours

def generate_circles ():
    image = np.ndarray ((400,400,3), dtype = np.uint8)
    image.fill (0)
    cv2.circle (image, (200,200), 100, (255,255,255), 2, cv2.LINE_AA)
    
    contours = []
    #cwd = os.getcwd ()
    for x in range (360):
        matrix = cv2.getRotationMatrix2D ((200, 200), x ,1)
        image2 = cv2.warpAffine (image, matrix, (400, 400))
        #path = os.path.join (cwd, 'tmp', 'circle-' + str (x) + '.jpg')
        #cv2.imwrite (path, image2)
        c = cv2.Canny (image2, 200, 400)
        i, cn, hr = cv2.findContours (c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        dispersion = contour_to_dispersion_hash (cn [0])
        if dispersion not in contours:
            contours.append (dispersion)
        
    return contours

# Finally, the Shaji, has come back, to Cicada!
# 17.01.2017
class ContourChainInput (Input):
    def poll (self):
        cn = self.ui.get_focus (raw = True, multi = True)
        image = self.ui.get_frame ()
        if cn is None:
            return None
        #elif not isinstance (cn, np.ndarray) and cn.shape [2] == 2:
        elif not isinstance (cn, list) or not len (cn) > 0:
            #warn ('{} of length {} passed!'.format (type (cn), len (cn)))
            return None
            #raise TypeError
        elif not isinstance (cn [0], np.ndarray):
            #warn ('list of {} returned!'.format (type (cn [0])))
            return None
        
        chain = str ()
        for c in cn:
            #print (c)
            dispersion = contour_to_dispersion_hash (c)
            chain += dispersion

        return Contour (chain)

def copy_contour_frame (image, cn, bg = (255,255,255)):
    dest = np.ndarray (image.shape, image.dtype)
    #dest.fill (255)
    dest [:] = bg
    for a in cn:
        #print (a)
        dest [a [0][1]][a[0][0]] = image [a[0][1]][a[0][0]]
        #print (dest [a [0][1]][a[0][0]])
    return dest


#def get_corners (cn):
    #'''
    #in: contour
    #out: top_left, top_right,  bottom_left, bottom_right
    #'''
    
    
