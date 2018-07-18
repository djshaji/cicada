#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-07-08

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, GLib, Pango
import json
from colour import Color
from storage.storage import Storage
from input.visual import cv2_image_to_gdk_pixbuf
import cv2
import numpy as np
from utils import Thread

class Colour (Storage):
    def __init__ (self, ui):
        #super (Colour, self).__init__ (ui)
        self.ui = ui
        self.known_data_types = [str, tuple]

    def query (self, text):
        c = None

        if isinstance (text, tuple):
            tt = (int (text [2]) / 255, int (text[1]) / 255, int (text[0]) / 255)
            c = Color (rgb = tt)

        elif isinstance (text, str):
            try:
                if text [0] == '#':
                    c = Color (text)
                elif text [0] == '(':
                    t = text [1:-1].split (',')
                    tt = (int (t [2]) / 255, int (t[1]) / 255, int (t[0]) / 255)
                    c = Color (rgb = tt)
                else:
                    #raise NotImplementedError ('color {} not understood!'.format (text))
                    return False
            except Exception as e:
                #print (e)
                return False
        
        if c is None:
            return False
        else:
            return c.get_web () [0] != '#'
    
    def get (self, text):
        c = None

        if isinstance (text, tuple):
            tt = (int (text [2]) / 255, int (text[1]) / 255, int (text[0]) / 255)
            c = Color (rgb = tt)

        elif isinstance (text, str):
            try:
                if text [0] == '#':
                    c = Color (text)
                elif text [0] == '(':
                    t = text [1:-1].split (',')
                    tt = (int (t [2]) / 255, int (t[1]) / 255, int (t[0]) / 255)
                    c = Color (rgb = tt)
                else:
                    raise NotImplementedError ('color {} not understood!'.format (text))
            except Exception as e:
                #print (e)
                return None
        
        return c.get_web ()
        #if type (text) == str and text [0] != '#' and text [0] != '(':
            #return (int (c.blue * 255), int (c.green * 255), int (c.red * 255))
        #else:
            #return c.get_web ()
        
class XKCD (Storage):
    tolerance = 10
    xkcd_names = json.loads (open ('storage/xkcd-colors.json').read ())
    xkcd_colors = dict ()
    for x in xkcd_names:
        xkcd_colors [xkcd_names [x]] = x
    
    def __init__ (self, ui):
        self.ui = ui
        self.known_data_types = [str, Color]

    def get_best_match (self, color):
        dif = []
        for i in self.xkcd_colors:
            res = int (color [1:], base = 16) - int (i [1:], base = 16)
            if res < 0:
                res = res * -1
            dif.append ((res, i))
        
        dif.sort ()
        print (dif)
        if dif [0][0] > 0 and dif [0][0] < self.tolerance:
            return dif [0][1]
        elif dif [0][0] < 0 and dif [0][0] > self.tolerance * -1:
            return dif [0][1]
        else:
            return None

    def query (self, text):
        if isinstance (text, Color):
            text = str (text)
            
        if text in self.xkcd_colors:
            return True
        elif text in self.xkcd_names:
            return True
        #elif self.get_best_match (text):
            #return True
        else:
            return False
        
    def get (self, text):
        if isinstance (text, Color):
            text = str (text)

        if text in self.xkcd_colors:
            return self.xkcd_colors [text]
        elif text in self.xkcd_names:
            return self.xkcd_names [text]
        else:
            return None #self.get_best_match (text)


class XKCDBrowser (Gtk.Window):
    xkcd_names = json.loads (open ('storage/xkcd-colors.json').read ())

    ICON_SIZE = 96
    
    shortcuts = {
        Gdk.KEY_F10: lambda self: self.unmaximize () if self.is_maximized () else self.maximize (),
        Gdk.KEY_F5: lambda self: self.reload (),
        Gdk.KEY_Delete: lambda self: self.delete (),
        Gdk.KEY_Escape: lambda self: self.destroy ()
    }

    def generate_icon1 (self, color, size = -1):
        if size == -1:
            size = self.ICON_SIZE
        
        pixbuf = GdkPixbuf.Pixbuf.new (0, 0, 8, size, size)
        #color = Color (color)
        #pixbuf.fill (Gdk.RGBA (red = color.red, green = color.green, blue = color.blue).to_color ())
        pixbuf.fill (int (color [1:], base = 16))
        return pixbuf

    def generate_icon (self, color, size = -1):
        if size == -1:
            size = self.ICON_SIZE
        im = np.ndarray ((size, size, 3))
        c = Color (color)
        #im.fill (c.blue)
        im [:] = (c.blue * 255, c.green * 255, c.red * 255)
        #print (c.blue, c.green, c.red)
        pixbuf = cv2_image_to_gdk_pixbuf (im)
        #GObject.Object.ref_sink (pixbuf)
        return pixbuf

    def fill_store_thread (self, mythread, thread_number):
        list_ = mythread.args ['list']
        len_ = len (list_)
        store = []
        
        for x in range (thread_number * int (len_ / mythread.threads),
                        (thread_number + 1) * int (len_ / mythread.threads)):
            store.append ([self.generate_icon (list_ [x][1]).copy (), list_ [x][0]])

        mythread.queues [thread_number].put (store)

    def item_activated (ui, self, path):
        it = self.ui.store.get_iter (path)
        name = self.ui.store.get (it, 1) [0]

        p = Gtk.Popover.new (ui.toolbar)
        image = Gtk.Image ()
        image.set_from_pixbuf (ui.generate_icon (ui.xkcd_names [name], size = 400))
        box = Gtk.VBox ()
        box.pack_start (image, 1, 1, 0)
        label = Gtk.Label (name + '\n' + ui.xkcd_names [name])
        label.set_justify (2)
        box.pack_start (label, 0, 0, 0)
        p.add (box)
        #p.set_size_request (200, 200)
        #p.set_position (2)
        p.show_all ()


    def fill_store (self):
        for name in self.xkcd_names:
            pixbuf = self.generate_icon (self.xkcd_names [name])
            self.store.append ([pixbuf, name])
        #list_ = []
        #for name in self.xkcd_names:
            #list_.append ([name, self.xkcd_names [name]])
            
        #args = {
            #'list': list_,
            #'store': self.store
        #}
        
        #mythread = Thread (4, self.fill_store_thread, args)
        #mythread.start ()
        #stores = mythread.get_data ()
        #mythread.join ()
        
        #for s in stores:
            #for i in s:
                #self.store.append ([i [0], i [1]])
                #print  ([i [0], i [1]])

    
    def hotkeys (self, window, event):
        if event.keyval in self.shortcuts:
            self.shortcuts [event.keyval] (self)
            return True

        
    def build_ui (self):
        self.iconview = Gtk.IconView ()
        self.iconview.ui = self
        self.iconview.sw = Gtk.ScrolledWindow ()
        self.iconview.sw.add (self.iconview)
        
        self.master = Gtk.HBox ()
        self.add (self.master)
        
        self.toolbar = Gtk.Toolbar ()
        self.box = Gtk.VBox ()
        
        self.master.pack_start (self.box, 1, 1, 0)
        self.box.pack_start (self.iconview.sw, 1, 1, 0)
        self.box.pack_end (self.toolbar, 0, 1, 0)
              
        self.store = Gtk.ListStore (GdkPixbuf.Pixbuf, str)
        self.store.set_sort_column_id (1, 0)
        self.fill_store ()
        
        self.iconview.connect ('item-activated', self.item_activated)
        
        self.iconview.set_model (self.store)
        self.iconview.set_item_width (96)
        
        self.iconview.set_pixbuf_column (0)
        self.iconview.set_text_column (1)
        
        self.connect ('key-press-event', self.hotkeys)
        self.connect ('destroy', self.main_quit)
        
        self.iconview.grab_focus ()
        
        pango_font = Pango.FontDescription.from_string ("Ubuntu 27")
        self.modify_font (pango_font)
        
        self.set_size_request (800, 500)
        self.show_all ()
    
    def main (self):
        try:
            self.mainloop.run ()
        except KeyboardInterrupt:
            print ("Keyboard Interrupt")
            self.main_quit ()
    
    def __init__ (self):
        Gtk.Window.__init__ (self)
        self.mainloop = GLib.MainLoop()
        self.build_ui ()
    
    def main_quit (self, *args):
        self.mainloop.quit ()

def xkcd_browser ():
    b = XKCDBrowser ()
    b.main ()

if __name__ is '__main__':
    xkcd_browser ()
