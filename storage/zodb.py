#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-07-08

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, GLib, Pango
import ZODB, ZODB.FileStorage
from ZEO import ClientStorage
import persistent
import os
import transaction
import BTrees.OOBTree
import inspect
from colour import Color
from input.visual import cv2_image_to_gdk_pixbuf, gdk_pixbuf_scale

if not __name__ == "__main__":
    from storage.storage import Storage
else:
    from storage import Storage

class ZODBStorage (Storage, persistent.Persistent):
    #default_database = os.path.expanduser ("~/.cicada/storage")
    default_database = "localhost", 9100
    commit = transaction.commit
    abort = transaction.abort

    root = None

    create_node = BTrees.OOBTree.BTree
    
    # More specialized storage classes may exist
    # accepts_data_type = lambda self, data_type: True

    def __init__ (self):
        self.query = self.exists
        #if not os.path.exists (self.default_database):
            #os.makedirs (os.path.dirname (self.default_database), exist_ok = True)
            
        #self.zodb_storage = ZODB.FileStorage.FileStorage (self.default_database)
        self.zodb_storage = ClientStorage.ClientStorage (self.default_database)
        self.zodb = ZODB.DB (self.zodb_storage)
        
    def open (self, node = "default"):
        self.zodb_connection = self.zodb.open ()
        self.root = self.zodb_connection.root ()

        if node:
            if not node in self.root:
                self.root [node] = BTrees.OOBTree.BTree ()
            self.root = self.root [node]
        return self.root
    
    def close (self):
        self.zodb_connection.close ()
        self.zodb.close ()
        self.zodb_storage.close ()

    def exists (self, *args):
        #print (args)
        path = None
        if self.root is not None:
            path = self.root
        else:
            return False
        
        for x in range (len (args)):
            #print (type (args [x]))
            if path.has_key (args [x]):
                path = path [args [x]]
            else:
                return False
        return True

    def set (self, *args):
        path = self.root
        for x in range (len (args) - 1):
            if not path.has_key (args [x]):
                path [args [x]] = BTrees.OOBTree.BTree ()
                #print (args [x], x)
            path = path [args [x]]

        path [args [-1]] = args [-1]
        #print (args [-1])

    def link (self, key, value):
        assert (type (key) == list and type (value) == list), "expected type list, got {} and {}". format (type (key).__name__, type (value).__name__)
        node1 = self.root
        node2 = self.root
        x = y = None
        
        for x in range (len (key) -1):
            if not node1.has_key (key [x]):
                node1 [key [x]] = self.create_node ()
            node1 = node1 [key [x]]

        for y in value:
            if not node2.has_key (y):
                node2 [y] = self.create_node ()
            node2 = node2 [y]

        #node1 [y] = self.create_node ()
        #node2 [x] = self.create_node ()
        
        node1 [key[-1]] = node2
        #node2 [x] = node1
        #print (key [-1], node1 [key [-1]])
        #print (node1 [y], node2 [x])

    def get (self, *args, recursive = True):
        path = self.root
        #print (args)
        for x in range (len (args)):
            if not path.has_key (args [x]):
                return None
            path = path [args [x]]

        if type (path) != BTrees.OOBTree.OOBTree:
            if recursive:
                return [path]
            else:
                return path
        
        items = []
        for i in path:
            items .append (i)
        
        if not recursive:
            return items [0]
        else:
            return items

    def print_db (self, node = None, level = 0, maxdepth = 5):
        if node == None:
            node = self.root
            
        for i in node:
            print ("--" * level, i)
            #print (i, type (node [i]))
            if level > maxdepth:
                break
            if type (node [i]) == BTrees.OOBTree.OOBTree:
                self.print_db (node [i], level + 1)
            
    def get_nodes (self, root):
        if root is None:
            root = self.root
        
        ret = []
        for r in root:
            ret.append ((r, root [r]))
        
        return ret

    def delete (self, *args):
        path = self.root
        # prevent rm -rf /
        if len (args) < 1:
            return
        elif isinstance (args [0], list) or isinstance (args [0], tuple):
            args = args [0]
            (frame, filename, line_number, function_name, lines, index) = inspect.getouterframes (inspect.currentframe()) [2]
            debug_info = "{}:{} {}".format (os.path.basename (filename).split (".") [0], line_number, function_name)
            print ('{}: Warning! Converting list to argument vector!'.format (debug_info))

        for x in range (len (args) - 1):
            if isinstance (path, persistent.mapping.PersistentMapping) and args [x] not in path:
                return
            elif isinstance (path, BTrees.OOBTree.OOBTree) and not path.has_key (args [x]):
                return
            
            path = path [args [x]]
        
        del (path [args [-1]])
        self.commit ()

class ZODBDataSource (Storage):
    storage = ZODBStorage ()
    close = storage.close
    #get = storage.get
    root = None

    def __init__ (self, ui):
        self.ui = ui
        self.known_data_types = [str, tuple, Color]
  
    def open (self):
        self.root = self.storage.open (node = "database")
    
    def set (self, key, value):
        #self.storage.set ("type", type (key), key, "__default__")
        #self.storage.set ("type", type (value), value, "__default__")
        #if self.root == None:
            #self.open ()
        
        self.open () if self.root is None else True
        self.storage.link (["type", str (type (key).__name__), str (key), str (type (value).__name__), str (value)], ["type", str (type (value).__name__), str (value)])
        self.storage.link (["type", str (type (value).__name__), str (value), str (type (key).__name__), str (key)], ["type", str (type (key).__name__), str (key)])
        self.storage.commit ()
        #print (self.root, self.get (key))
        
    def query (self, key):
        self.open () if self.root is None else True
        if self.root == None:
            return False
        
        return self.storage.query ("type", str (type (key).__name__), str (key))
    
    def get (self, key):
        self.open () if self.root is None else True
        types = self.storage.get ("type", str (type (key).__name__), str (key))
        res = dict ()
        for i in types:
            #print (i, type (self.storage.get ("type", str (type (key).__name__), str (key), str (i))))
            res [i] = self.storage.get ("type", str (type (key).__name__), str (key), str (i), recursive = False)
        return res
        
import input.contour
class Browser (Gtk.Window):
    storage = ZODBStorage ()
    icon_theme = Gtk.IconTheme.get_default ()
    
    ICON_SIZE = 96
    
    folder_p = icon_theme.load_icon ('folder', ICON_SIZE, Gtk.IconLookupFlags.GENERIC_FALLBACK)
    file_p = icon_theme.load_icon ('text-x-generic', ICON_SIZE, Gtk.IconLookupFlags.GENERIC_FALLBACK)
    
    pixbufs = {
        BTrees.OOBTree.OOBTree: folder_p,
        str: file_p
    }

    shortcuts = {
        Gdk.KEY_F10: lambda self: self.unmaximize () if self.is_maximized () else self.maximize (),
        Gdk.KEY_F5: lambda self: self.reload (),
        Gdk.KEY_Delete: lambda self: self.delete (),
        Gdk.KEY_Escape: lambda self: self.destroy ()
    }

    shortcuts_meta = {
        #Gdk.KEY_equal: lambda self: self.icon_zoom (True),
        #Gdk.KEY_minus: lambda self: self.icon_zoom (False),
        Gdk.KEY_Up: lambda self: self.up (),
        Gdk.KEY_Home: lambda self: self.home ()
    }

    def delete (self, *args):
        items = self.iconview.get_selected_items ()
        nodes = []

        parent = self.addressbar.get_text ()
        
        for i in items:
            it = self.store.get_iter (i)
            node = self.store.get (it, 1) [0]
            
            node = parent + node
            vector = node.split ('/')
            for v in vector:
                if v == '':
                    del (vector [vector.index (v)])
            self.storage.delete (vector)
        
        self.reload ()

    def icon_zoom (self, zoom):
        if zoom:
            self.ICON_SIZE += 24
        else:
            self.ICON_SIZE -= 24
        self.folder_p = self.icon_theme.load_icon ('gtk-directory', self.ICON_SIZE, Gtk.IconLookupFlags.GENERIC_FALLBACK)
        self.file_p = self.icon_theme.load_icon ('gtk-file', self.ICON_SIZE, Gtk.IconLookupFlags.GENERIC_FALLBACK)
    
    
    def reload (self, *args):
        parent = self.addressbar.get_text ()
        self.open (parent)
    
    def is_contour (self, name):
        for e in name:
            if not e.isdigit ():
                return False
        return True
    
    def is_color (self, name):
        if name [0] == '#' and len (name) == 7:
            return True
        else:
            return False
        
    def up (self, *args):
        parent = self.addressbar.get_text ()
        if parent == '/':
            return
        elif parent [-1] == '/':
            parent= parent [:-1]
        
        self.open (os.path.dirname (parent))
    
    def home (self, *args):
        self.open (node = '/')
    
    def item_activated (ui, self, path):
        it = self.ui.store.get_iter (path)
        node = self.ui.store.get (it, 1) [0]
        self.ui.open (node)

    def hotkeys (self, window, event):
        #print (Gdk.keyval_name (event.keyval), int (event.state))
        if int (event.state) == 24 or int (event.state) == 8:
            if event.keyval in self.shortcuts_meta:
                self.shortcuts_meta [event.keyval] (self)
            return True

        if event.keyval in self.shortcuts:
            self.shortcuts [event.keyval] (self)
            return True

    def get_contour_pixbuf (self, contour):
        cn = input.contour.dispersion_to_contour (contour, scale = 2)
        image = input.contour.generate_image_from_contour (cn)
        pixbuf = cv2_image_to_gdk_pixbuf (image)
        pixbuf = gdk_pixbuf_scale (pixbuf, self.ICON_SIZE, self.ICON_SIZE)
        return pixbuf

    def get_color_pixbuf (self, color, size = -1):
        if size == -1:
            size = self.ICON_SIZE
        
        pixbuf = self.new_pixbuf (size)
        pixbuf.fill (int (color [1:] + 'ff', base = 16))
        return pixbuf        

    def new_pixbuf (self, size):
        # real ugly way to get an empty pixbuf
        return self.icon_theme.load_icon (self.icon_theme.get_example_icon_name (), size, Gtk.IconLookupFlags.FORCE_SIZE)

    def open (self, node = None):
        parent = self.addressbar.get_text ()
        if not parent:
            parent = '/'
        if not node:
            node = str ()
            node = parent + node
        elif not node [-1] == '/':
            node += '/'
        
        if len (node) > 1 and not node [0] == '/':
            node = parent + node
        
        self.addressbar.set_text (node)
        self.store.clear ()

        vector = node.split ('/')
        node = self.root
        for x in range (len (vector)):
            if vector [x] == '':
                continue
            if isinstance (node, persistent.mapping.PersistentMapping) and vector [x] not in node:
                break
            elif isinstance (node, BTrees.OOBTree.OOBTree) and not node.has_key (vector [x]):
                break
            node = node [vector [x]]
        
        ret = self.storage.get_nodes (node)
        for r in ret:
            pixbuf = None
            if self.is_color (r [0]):
                pixbuf = self.get_color_pixbuf (r [0])
                if isinstance (r [1], BTrees.OOBTree.OOBTree):
                    self.pixbufs [type (r [1])].copy ().composite (pixbuf, 0, 0, 48, 48, 0, 0, .5, .5, GdkPixbuf.InterpType.NEAREST, 80)
            elif self.is_contour (r [0]):
                pixbuf = self.get_contour_pixbuf (r [0])
                if isinstance (r [1], BTrees.OOBTree.OOBTree):
                    self.pixbufs [type (r [1])].copy ().composite (pixbuf, 0, 0, 48, 48, 0, 0, .5, .5, GdkPixbuf.InterpType.NEAREST, 80)
            else:
                pixbuf = self.pixbufs [type (r [1])]

            self.store.append ([pixbuf, r [0]])
        
    def build_ui (self):
        self.iconview = Gtk.IconView ()
        self.iconview.ui = self
        self.iconview.connect ('item-activated', self.item_activated)
        self.iconview.sw = Gtk.ScrolledWindow ()
        self.iconview.sw.add (self.iconview)

        self.iconview.set_item_width (120)
        
        self.master = Gtk.HBox ()
        self.add (self.master)
        
        self.addressbar = Gtk.Entry ()
        self.addressbar.ui = self
        self.addressbar.connect ('activate', lambda self, *w: self.ui.open ())
        
        self.toolbar = Gtk.Toolbar ()
        
        self.addressbar.toolitem = Gtk.ToolItem ()
        self.addressbar.toolitem.add (self.addressbar)

        self.addressbar.toolitem.set_expand (True)
        self.toolbar.up = Gtk.ToolButton.new_from_stock ('gtk-go-up')
        self.toolbar.home = Gtk.ToolButton.new_from_stock ('gtk-home')

        self.toolbar.up.connect ('clicked', self.up)
        self.toolbar.home.connect ('clicked', self.home)

        self.toolbar.insert (self.toolbar.up, -1)
        self.toolbar.insert (self.toolbar.home, -1)
        self.toolbar.insert (self.addressbar.toolitem, -1)

        self.box = Gtk.VBox ()
        self.box.pack_start (self.toolbar, 0, 0, 0)
        self.master.pack_start (self.box, 1, 1, 0)
        
        self.box.pack_start (self.iconview.sw, 1, 1, 0)
        self.store = Gtk.ListStore (GdkPixbuf.Pixbuf, str)
        self.store.set_sort_column_id (1, 0)
        
        self.iconview.set_model (self.store)
        
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
        self.root = self.storage.open (None)
        self.open (None)

    def main_quit (self, *args):
        self.mainloop.quit ()

def zodb_browser ():
    b = Browser ()
    b.main ()

if __name__ == "__main__":
    zodb_browser ()
    #db = ZODBDataSource (None)
    #db.open ()
    #d = db.get ('pia')
    #print (d)
    #db = ZODBStorage ()
    #db.open ("test")
    #transaction.commit ()
    #db.storage.print_db ()
    ##db.close ()
    #db.set ('name', 'tim')
    #print (db.get ('name', 'tim'))
