#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-23

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, GLib, Pango
import warnings, os, sys, glob
import multiprocessing
from enum import Enum
from hash_commands import HashCommands
from sounds import Sounds
from version import version, get_version
from time import time, sleep
from input.visual import VideoInput, ColorFocus, cv2_image_to_gdk_pixbuf, ColorInput, Picture, gdk_pixbuf_scale, gdk_color_to_cv2
from argparse import ArgumentParser
import copy
import cv2
import numpy as np
from cog import Cog
from colour import Color
from curiosity import Curiosity
from input.visualsensoryinput import VisualSensoryInput
from storage.fortune import Fortune
from storage.color import Colour, XKCD, xkcd_browser
from storage.zodb import ZODBDataSource, zodb_browser
from utils import debug_info, Timer, Pool, debug
from input.contour import ContourFocus, ContourInput, ContourStorage, ContourClusterInput, ContourClusterStorage, AutoContourClusterInput, ContourChainInput, generate_image_from_contour, dispersion_to_contour
from input.ocr import OCRInput
from input.featuredetect import FastFocus, OrbFocus
from input.qr import QRInput
from input.shape import ShapeInput, ShapeStorage
from introspection import Introspection
from plugin import PluginHost
from filters import FilterHost
from input.bridge import BridgeInput

class FocusMode (Enum):
    raw = 0
    color = 1
    contour = 2
    contour_es = 3
    contour_multi = 4
    contour_es_multi = 5
    # this was here before
    # would this break anything?
    # tune in next week!
    #contour_clusters = 6
    fast = 6
    fast_es = 7
    orb = 8
    orb_es = 9
    contour_clusters = 10

def resize_calculator (width, height, new_width, new_height):
    ratio = 1
    resized_width = 0
    resized_height = 0
    
    if width > height:
        ratio = width / height
        resized_width = new_width
        resized_height = new_width / ratio
    else:
        ratio = height / width
        resized_height = new_height
        resized_width = new_height * ratio

    #print (width, height, new_width, new_height, resized_width, resized_height, ratio)
    return resized_width, resized_height

def message_box (title, message, message_type):
    dialog = Gtk.MessageDialog (text = title, secondary_text = message, message_type = message_type, buttons = Gtk.ButtonsType.OK)
    dialog.run ()
    dialog.destroy ()

TextAttributeTags = [
    ("input", "DarkSeaGreen4", Pango.Weight.BOLD),
    ("cog", "darkcyan", Pango.Weight.BOLD),
    ("ui", "darkgreen", Pango.Weight.BOLD),
    ("error", "red", Pango.Weight.BOLD),
    ("hash", "darkorange", Pango.Weight.BOLD),
    #("you", "DarkTurquoise", Pango.Weight.BOLD),
    ("storage", "DarkTurquoise", Pango.Weight.BOLD),
    ("introspect", "#e17701", Pango.Weight.BOLD),
    ("you", "#869AA4", Pango.Weight.BOLD),
    #("info", "#869AA4", Pango.Weight.NORMAL),
    ("default", "#869AA4", Pango.Weight.NORMAL)
]

class CompletionHistory:
    history = []
    index = 0

    def append (self, text):
        if len (self.history) == 0 or (len (self.history) > 0 and text != self.history [-1]):
            self.history.append (text)
            self.reset ()
    
    def reset (self):
        self.index = len (self.history)
    
    def get_completion (self, direction = True):
        if len (self.history) == 0:
            return None
        
        if direction:
            if self.index > 0:
                self.index -= 1
        else:
            if self.index < len (self.history) - 1:
                self.index += 1
        
        return self.history [self.index]
    

class UI (Gtk.Window):
    class Mode (Enum):
        none = 0
        camera = 1
        picture = 2
        video = 3
        folder = 4
        canvas = 5

    #get_focus = lambda self: self.camera_get_focus ()
    #get_selection = lambda self: self.camera_get_focus ()
    sleep_interval = 100
    current_frame = None
    focused_pixbuf = None
    PREVIEW_ICON_SIZE = 64
    PREVIEW_DEFAULT_ICON = 'dialog-question'
    icon_theme = Gtk.IconTheme.get_default ()
    
    shortcuts = {
        Gdk.KEY_F6: lambda self: self.zoom_in (),
        Gdk.KEY_F5: lambda self: self.zoom_out (),
        Gdk.KEY_F7: lambda self: self.zoom_fit (),
        Gdk.KEY_F8: lambda self: self.zoom_100 (),
        #Gdk.KEY_Super_L: lambda self: self.menu_button.do_clicked (self.menu_button),
        Gdk.KEY_Menu: lambda self: self.menu_button.do_clicked (self.menu_button),
        #65360: lambda self: self.text_view_scroll_to_top (),
        #65367: lambda self: self.text_view_scroll_to_bottom (),
        Gdk.KEY_F1: lambda self: self.image_revealer.set_reveal_child (not self.image_revealer.get_reveal_child ()),
        Gdk.KEY_F2: lambda self: self.text_view_revealer.set_reveal_child (not self.text_view_revealer.get_reveal_child ()),
        Gdk.KEY_F3: lambda self: [self.button_box_revealer.set_reveal_child (not self.button_box_revealer.get_reveal_child ()), self.entry.grab_focus () if self.button_box_revealer.get_reveal_child () else 3],
        Gdk.KEY_F10: lambda self: self.unmaximize () if self.is_maximized () else self.maximize (),
        Gdk.KEY_Escape: lambda self: self.destroy () if not self.abort.is_visible () else self.abort.set_active (True),
        Gdk.KEY_Page_Down: lambda self: self.text_view_sw.get_vadjustment ().set_value (self.text_view_sw.get_vadjustment ().get_value () + 200),
        #65364: lambda self: self.text_view_sw.get_vadjustment ().set_value (self.text_view_sw.get_vadjustment ().get_value () + 20),
        #65362: lambda self: self.text_view_sw.get_vadjustment ().set_value (self.text_view_sw.get_vadjustment ().get_value () - 20),
        #65361: lambda self: self.text_view_sw.get_hadjustment ().set_value (self.text_view_sw.get_hadjustment ().get_value () + 20),
        #65363: lambda self: self.text_view_sw.get_hadjustment ().set_value (self.text_view_sw.get_hadjustment ().get_value () - 20)
        Gdk.KEY_Page_Up: lambda self: self.text_view_sw.get_vadjustment ().set_value (self.text_view_sw.get_vadjustment ().get_value () - 200)
        #Gdk.KEY_Up: lambda self: self.entry_history_complete (),
        #Gdk.KEY_Down: lambda self: self.entry_history_complete (False)
    }

    shortcuts_meta = {
        Gdk.KEY_1: lambda self: self.notebook.set_current_page (0),
        Gdk.KEY_0: lambda self: self.entry.grab_focus (),
        Gdk.KEY_2: lambda self: self.notebook.set_current_page (1),
        Gdk.KEY_3: lambda self: self.notebook.set_current_page (2),
        Gdk.KEY_4: lambda self: self.notebook.set_current_page (3),
        Gdk.KEY_5: lambda self: self.notebook.set_current_page (4),
        Gdk.KEY_Up: lambda self: self.entry_history_complete (),
        Gdk.KEY_Down: lambda self: self.entry_history_complete (False)
    }

    shortcuts_ctrl = {
        Gdk.KEY_Up: lambda self: self.entry_history_complete (),
        Gdk.KEY_Down: lambda self: self.entry_history_complete (False)
    }

    def init_input (self):
        color_input = ColorInput (self)
        self.cog.add_input (color_input, "color")
        self.cog.add_input (ContourInput (self), "contour")
        self.cog.add_input (ContourClusterInput (self), "contour-cluster")
        self.cog.add_input (ContourChainInput (self), "contour-chain")
        #self.cog.add_input (AutoContourClusterInput (self), "auto-contour-cluster")
        self.cog.add_input (OCRInput (self), 'ocr')
        self.cog.add_input (QRInput (self), 'qr')
        self.cog.add_input (ShapeInput (self), 'shape')

    def init_config (self):
        # pull in defaults from modules
        self.contour.spin1.set_value (self.contourfocus.getattr ('canny1'))
        self.contour.spin2.set_value (self.contourfocus.getattr ('canny2'))
        self.contour.thickness.set_value (self.contourfocus.getattr ('thickness'))
        self.contour.flip_axis.set_value (self.contourfocus.getattr ('flip_axis'))
        self.contour.draw_all.set_active (self.contourfocus.getattr ('draw_all_contours'))
        self.contour.draw_only.set_active (self.contourfocus.getattr ('draw_only_contours'))
        self.contour.flip.set_active (self.contourfocus.getattr ('flip'))
        self.contour.randomize.set_active (self.contourfocus.getattr ('randomize'))
        self.contour.mode.set_active (self.focus_mode.value)

        for i in self.contourfocus.CannyModes:
            #print (i.value, i.name)
            self.contour.canny_mode.insert_text (i.value, str (i.name))

        for i in self.fastfocus.Types:
            self.fast.type.insert_text (i.value, str (i.name))

        for i in self.contourfocus.CannyMethods:
            #print (i.value, i.name)
            #print (self.contourfocus.CannyMethods [i.name].value)
            self.contour.canny_method.insert_text (i.value, str (i.name))
        
        self.contour.canny_mode.set_active (self.contourfocus.mode)
        self.contour.canny_method.set_active (self.contourfocus.method - 1) # hack!
        selection_color = self.contourfocus.getattr ('selection_color')
        self.contour.color.set_rgba (Gdk.RGBA (red = selection_color [2] / 255, green = selection_color [1] / 255, blue = selection_color [0] / 255))
        selection_color = self.contourfocus.getattr ('es_color')
        self.contour.es_color.set_rgba (Gdk.RGBA (red = selection_color [2] / 255, green = selection_color [1] / 255, blue = selection_color [0] / 255))

        self.fast.threshold.set_value (self.fastfocus.getThreshold ())
        self.fast.type.set_active (self.fastfocus.getType ())
        self.fast.nms.set_active (self.fastfocus.getNonmaxSuppression ())
        self.fast.draw_only_key_points.set_active (self.fastfocus.draw_only_key_points)
        
        self.orb.edge_threshold.set_value (self.orbfocus.orb.getEdgeThreshold ())
        self.orb.fast_threshold.set_value (self.orbfocus.orb.getFastThreshold ())
        self.orb.first_level.set_value (self.orbfocus.orb.getFirstLevel ())
        self.orb.max_features.set_value (self.orbfocus.orb.getMaxFeatures ())
        self.orb.n_levels.set_value (self.orbfocus.orb.getNLevels ())
        self.orb.patch_size.set_value (self.orbfocus.orb.getPatchSize ())
        self.orb.scale_factor.set_value (self.orbfocus.orb.getScaleFactor ())
        self.orb.score_type.set_value (self.orbfocus.orb.getScoreType ())
        
    def init_storage (self):
        #fortune = Fortune (self)
        self.cog.add_data_source (Fortune (self), "fortune")
        self.cog.add_data_source (Colour (self), "colour")
        self.cog.add_data_source (XKCD (self), "xkcd")
        self.cog.add_data_source (ZODBDataSource (self), "zodb")
        self.cog.add_data_source (ContourClusterStorage (self), "contour-cluster")
        self.cog.add_data_source (ContourStorage (self), "contour")
        self.cog.add_data_source (ShapeStorage (self), "shape")
        
    def keyboard_shortcuts (self):
        msg = "Following shortcuts are available: "
        for key in self.shortcuts:
            msg = msg + Gdk.keyval_name (key) + " "
        
        self.message (msg)
        
    def text_view_scroll_to_top (self):
        self.text_view_sw.get_vadjustment ().set_value (self.text_view_sw.get_vadjustment ().get_lower ())

    def help (self):
        self.message (self.hasher.help (), "ui")

    def hotkeys (self, window, event):
        # aye!
        #if int (event.state) == 24 or int (event.state) == 8:
        if event.state == Gdk.ModifierType.MOD1_MASK:
            if event.keyval in self.shortcuts_meta:
                self.shortcuts_meta [event.keyval] (self)
                return True
        #print (Gdk.keyval_name (event.keyval), int (event.state))
        if event.state == Gdk.ModifierType.CONTROL_MASK:
            if Gdk.keyval_name (event.keyval).isdigit ():
                #self.set_focus_mode (event.keyval - 48) # aye, hack!
                # heh. clever. this
                if not self.focus_on:
                    self.focus_toggle (True)
                self.contour.mode.set_active (event.keyval - 48)
                
                # although there is the possiblity that this is
                # how it's done. 1 = 48. 
                # *_^
                return True
            elif event.keyval in self.shortcuts_ctrl:
                self.shortcuts_ctrl [event.keyval] (self)
                return True

        if event.keyval in self.shortcuts:
            self.shortcuts [event.keyval] (self)
            return True

    def get_response (self, message = None, module = "default"):
        if message:
            self.message (message, module)
        
        self.entry.set_progress_fraction (1)
        self.mainloop_response.run ()
        res = self.entry.get_text ()
        self.entry.set_text ("")
        self.entry.set_progress_fraction (0)
        return res

    def zoom_fit (self, *args):
        self.zoom_width = 0
        self.zoom_height = 0

    def zoom_100 (self, *args):
        self.zoom_width = -1
        self.zoom_height = -1

    def zoom_in (self, *args):
        #debug ('zoom')
        self.zoom_width, self.zoom_height = resize_calculator (self.zoom_width, self.zoom_height, self.zoom_width + 50, self.zoom_height + 50)

    def zoom_out (self, *args):
        self.zoom_width, self.zoom_height = resize_calculator (self.zoom_width, self.zoom_height, self.zoom_width - 50, self.zoom_height - 50)

    def plugins_list (self):
        msg = 'available plugins: '
        for i in self.plugin_host.get_plugins ():
            msg += i + ' '
        
        self.message (msg, 'hash')

    def entry_history_complete (self, direction = True):
        completion = self.entry_history.get_completion (direction)
        if completion:
            self.entry.set_text (completion)
            self.entry.set_position (-1)

    def parse_input (self, text):
        self.entry_history.append (text)
        self.entry_history.reset ()
        if self.mainloop_response.is_running ():
            self.mainloop_response.quit ()
            return
        
        self.entry.set_text ("")
        if text [0] == '#':
            ret_msg = self.hasher.run (text)
            if ret_msg:
                self.message (ret_msg, "hash")
        elif text [0] == '%':
            if text == '%':
                self.plugins_list ()
                return
            
            ret_msg = self.plugin_host.run (text [1:])
            if ret_msg:
                self.message (ret_msg, "hash")
        else:
            self.cog.process (text)

    def init_plugins (self):
        self.plugins = {}
        for i in self.manager.plugin_host.get_plugins ():
            #self.plugins [i] = lambda *w: self.manager.plugin_host.run (i)
            self.plugins [i] = lambda *w: print (i)
            self.hasher.append ('plugin-' + i, self.plugins [i])
            self.entry_completion_append ('plugin-' + i)

    def __init__ (self, manager = None, mode = None, uri = None):
        Gtk.Window.__init__ (self)
        self.manager = manager
        self.stop_video = self.stop_camera
        self.mainloop = GLib.MainLoop()
        self.maincontext = self.mainloop.get_context ()
        self.mainloop_response = GLib.MainLoop ()
        self.maincontext_response = self.mainloop_response.get_context ()
        self.hasher = HashCommands (self)
        self.timer = Timer ()
        self.message = self.append_text
        self.connect ("key-press-event", self.hotkeys)
        #self.resize (640, 480)
        self.connect ("destroy", lambda *w: self.main_quit ())
        self.set_position (Gtk.WindowPosition.CENTER_ALWAYS)
        self.filter_host = FilterHost (self)
        self.build_ui ()
        self.set_default_icon_from_file ("ui-resources/icon-small.png")
        self.camera = VideoInput (self)
        self.get_focus = self.camera_get_focus
        self.get_selection = self.camera_get_focus
        self.colorfocus = ColorFocus ()
        self.contourfocus = ContourFocus (self)
        self.fastfocus = FastFocus (self)
        self.orbfocus = OrbFocus (self)
        self.focus_on = False
        self.focus_mode = FocusMode.color
        self.entry_history = CompletionHistory ()
        self.cog = Cog (self)
        self.curiosity = Curiosity (self)
        self.curiosity.register_sensory_input (VisualSensoryInput (self))
        self.init_input ()
        self.init_storage ()
        self.init_config ()
        #self.init_plugins () broken :(
        self.sounds = Sounds ()
        self.plugin_host = PluginHost (ui = self)
        self.introspection = Introspection (self)
        self.introspection.add_module (__builtins__)
        self.introspection.add_module (self)
        for i in self.introspection.get_completion ():
            self.entry_completion_store.set_value (self.entry_completion_store.append (), 0, "#introspect;" + str (i))
            #print ("#introspect;" + str (i))
        self.dragging = False
        #self.set_progress = self.entry.set_progress_fraction
        self.realize ()
        self.update_ui ()
        if mode:
            #GLib.idle_add (lambda *w: self.open_modes [mode] (self, uri = uri))
            self.manager.idle_add (lambda *w: self.open_modes [mode] (self, uri = uri))
            #GLib.idle_add (self.main)
    

    def bridge_input_start (self, id = 0, focus_only = False):
        # wat?
        #if focus_only:
            #self.camera = BridgeInput (manager = self.manager, id = id, focus_only = True)
        #else:
            #self.camera = BridgeInput (manager = self.manager, id = id)
        self.camera = BridgeInput (manager = self.manager, id = id, focus_only = focus_only)
        self.play (self.camera)
    
    def bridge_input_start_hook (self, *args):
        if len (args) > 1 and len (args [1]) > 1 and args [1][0].isdigit () and args [1][1].isdigit () and bool (args [1][1]):
            self.bridge_input_start (int (args [1][0]), focus_only = True)
        elif len (args) > 1 and args [1][0].isdigit ():
            self.bridge_input_start (int (args [1][0]))
        else:
            self.message ("Enter window id!", 'ui-error')

    def progress_set (self, fraction, message = None):
        self.abort.set_active (False)
        self.abort.show ()
        self.entry.set_progress_fraction (fraction)
        self.entry.set_sensitive (False)
        if message:
            self.entry.set_text (message)
    
    def progress_reset (self):
        self.entry.set_progress_fraction (0)
        self.entry.set_sensitive (True)
        self.entry.set_text ('')
        self.abort.hide ()
        self.entry.grab_focus ()
    
    def introspect (self, *w):
        if len (w) > 1:
            w = w [1:] [0]
            retval = self.introspection.introspect (w)
            self.info (str (retval))
            self.update_ui ()
            self.message (retval, 'introspect')
        
    def focus_toggle (self, focus = False):
        self.focus_on = focus
        self.message ("Focus turned {}".format (str(focus)))
    
    def main (self):
        self.show_all ()
        self.sounds.play ('default')
        try:
            self.mainloop.run ()
        except KeyboardInterrupt:
            print ("Keyboard Interrupt")
            self.main_quit ()

    def set_image (self, name):
        image = None
        if type (name) == GdkPixbuf.Pixbuf:
            image = name
        elif type (name) is np.ndarray:
            image = cv2_image_to_gdk_pixbuf (name)
        elif os.path.exists (name):
            image = GdkPixbuf.Pixbuf.new_from_file (name)
        else:
            raise NotImplementedError ("unknown image type {}".format (name))
        
        if self.zoom_width is 0 or self.zoom_height is 0:
            self.zoom_width, self.zoom_height = self.get_default_zoom ()
            self.zoom_width, self.zoom_height = resize_calculator (image.get_width (), image.get_height (), self.zoom_width, self.zoom_height)
        elif self.zoom_width is -1 or self.zoom_height is -1:
            self.zoom_width = image.get_width ()
            self.zoom_height = image.get_height ()
            
        image = image.scale_simple (self.zoom_width, self.zoom_height, GdkPixbuf.InterpType.BILINEAR)
        self.image.set_from_pixbuf (image)

    def screenshot (self, *w):
        self.camera.close ()
        self.picture_load (fname = self.current_frame)
    
    def error (self, message):
        self.message (message, 'ui-error')
    
    def canvas_new_image (self, width = 0, height = 0, canvas = None):
        if canvas:
            if 'x' in canvas:
                res = args.canvas.split ('x')
                width = int (res [0])
                height = int (res [1])
            
        if not width or not height:
            width, height = self.prompt_vars ([int, int], message = 'Enter dimensions')
        image = np.ndarray ((height, width, 3), dtype = np.uint8)
        image.fill (255)
        self.picture_load (fname = image)

    def canvas_draw_text (self):
        frame = self.get_frame (raw = True)
        if frame is None:
            return None

        center, side = self.get_focus_coords (FocusMode.color)
        text, size = self.prompt_vars ([str, int], 'enter text and text size')
        cv2.putText (frame, text, (center [0] - size, center [1] + size), cv2.FONT_HERSHEY_PLAIN, size, self.contourfocus.selection_color, self.contourfocus.thickness)

    def canvas_draw_line (self):
        center, side = self.get_focus_coords (FocusMode.color)
        mode = self.prompt_vars ([int], message = 'Select direction') [0]
        if mode > 2:
            mode = 2
        start = end = 0
        if mode == 0:
            start = center [0] - side [0], center [1] - side [1]
            end = center [0] + side [0], center [1] + side [1]
        elif mode == 1:
            start = center [0] - side [0], center [1]
            end = center [0] + side [0], center [1]
        elif mode == 2:
            start = center [0], center [1] - side [1]
            end = center [0], center [1] + side [1]
            
        frame = self.get_frame (raw = True)
        if frame is None:
            return None
        
        cv2.line (frame, start, end, self.contourfocus.selection_color, self.contourfocus.thickness, cv2.LINE_AA)
    
    def canvas_clear (self, choose_color = False):
        frame = self.get_frame (raw = True)
        if not choose_color:
            frame.fill (255)
            return
        
        color = self.prompt_vars ([Gdk.Color], 'choose color') [0]
        frame [:] = gdk_color_to_cv2 (color)
    
    def canvas_draw_rect (self):
        center, side = self.get_focus_coords (FocusMode.color)
        start = center [0] - side [0], center [1] - side [1]
        end = center [0] + side [0], center [1] + side [1]
        frame = self.get_frame (raw = True)
        if frame is None:
            return None
        
        cv2.rectangle (frame, start, end, self.contourfocus.selection_color, self.contourfocus.thickness, cv2.LINE_AA)
    
    def canvas_draw_circle (self):
        center, side = self.get_focus_coords (FocusMode.color)
        frame = self.get_frame (raw = True)
        if frame is None:
            return None
        
        cv2.circle (frame, tuple (center), side [0], self.contourfocus.selection_color, self.contourfocus.thickness, cv2.LINE_AA)

    def picture_load (self, *args, fname = None):
        filename = None
        
        if fname is str or np.ndarray:
            filename = fname
        elif len (args) > 1:
            filename = args [1][0]
            self.start_camera (filename = filename)
            return
        if filename is None:
            filename = self.prompt_filename ()
        #warnings.warn ('fatafat likha hai check it')
        if filename is not None:
            if isinstance (filename, str):
                # takes a looong time sometimes
                #self.gallery_open (os.path.dirname (filename))
                self.message ("loaded image: {}".format (filename), "ui")
            else:
                self.message ('loaded image from memory', 'ui')
            
            self.camera = Picture (self)
            self.camera.open (filename)
            self.play (self.camera)
    
    def set_focus_mode (self, mode = FocusMode.color):
        if isinstance (mode, int):
            mode = FocusMode (mode)
        elif isinstance (mode, str):
            mode = FocusMode [mode]
        elif not isinstance (mode, FocusMode):
            raise NotImplementedError
        
        if mode.value:
            self.focus_mode = mode
            self.message ("focus mode set to {}".format (str (self.focus_mode)), 'ui')

    def entry_activate (self, entry):
        text = self.entry.get_text ()
        text = text.strip ()
        
        #if len (text) < 1 and not self.mainloop_response.is_running ():
            #return
        
        if len (text) > 0:
            self.message (text, "you")
            self.info (text)
        elif not self.mainloop_response.is_running ():
            return
        #self.entry.set_text ("")
        #self.entry_completion_store.set_value (self.entry_completion_store.append (), 0, text)
        self.parse_input (text)
    
    def assign (self, var, value):
        print (var, value)
        var = value
        print (var, value)
    
    def __reset_scale__ (self):
        frame = self.get_frame ()
        if frame is None:
            return
        
        height, width, something = frame.shape
        self.filters.scale.width.set_value (width)
        self.filters.scale.height.set_value (height)
    
    def main_quit (self):
        #print ("Goodbye")
        #if self.get_response ("Do you want to quit?") == 'y':
        if self.curiosity.mainloop.is_running ():
            self.curiosity.mainloop.quit ()

        if self.mainloop_response.is_running ():
            self.mainloop_response.quit ()
        if self.mainloop.is_running ():
            self.mainloop.quit ()
        
        self.manager.ui_remove (self)
    
    def logofy (self, error = False):
        p = GdkPixbuf.Pixbuf.new_from_file_at_scale ("ui-resources/logo.png", 640, 480, 1)
        if error:
            p = p.composite_color_simple (p.get_width (), p.get_height (), 2, 255, 32, 16711680, 16711680)
            #p = p.flip (True)
        
        self.image.set_from_pixbuf (p)
        #p = GdkPixbuf.PixbufAnimation.new_from_file ("ui-resources/logo.gif")
        #self.image.set_from_animation (p)

    def contour_update (self):
        self.contourfocus.set (canny1 = self.contour.spin1.get_value_as_int ()) 
        self.contourfocus.set (canny2 = self.contour.spin2.get_value_as_int ())
        #print (self.contourfocus.canny1)
    
    def text_view_clear (self, *args):
        self.text_buffer.set_text ("")

    def build_ui (self):
        self.master = Gtk.HBox ()
        self.add (self.master)
        
        self.box = Gtk.VBox ()
        self.master.pack_start (self.box, 1, 1, 0)
                     
        #self.infobar_box = Gtk.VBox ()
        self.infobar_revealer = Gtk.Revealer ()
        #self.infobar_box.pack_start (self.infobar_revealer, 0, 0, 0)

        self.infobar = Gtk.InfoBar ()
        self.infobar.label = Gtk.Label ()
        self.infobar.label.set_line_wrap (True)
        self.infobar.label.set_ellipsize (2)
        self.infobar.label.set_line_wrap_mode (2)
    
        self.infobar.image = Gtk.Image ()
        self.infobar.get_action_area ().add (self.infobar.image)
        #self.infobar.image.set_from_stock (self.PREVIEW_DEFAULT_ICON, self.PREVIEW_ICON_SIZE)
        
        self.infobar.get_content_area ().add (self.infobar.label)

        self.infobar_revealer.add (self.infobar)
        #self.infobar_box.props.halign = Gtk.Align.START
        #self.overlay.add_overlay (self.infobar_box)
        self.box.pack_start (self.infobar_revealer, 0, 0, 0)
        self.infobar.set_show_close_button (1)
        self.infobar.revealer = self.infobar_revealer
        self.infobar.connect ('response', lambda self, *w: self.revealer.set_reveal_child (False))

        self.image = Gtk.Image ()
        self.image_revealer = Gtk.Revealer ()
        self.image_revealer.set_reveal_child (True)
        self.image_event_box = Gtk.EventBox ()
        self.image_event_box.add (self.image)
        
        self.image_sw = Gtk.ScrolledWindow ()
        
        box1 = Gtk.HBox ()
        box2 = Gtk.VBox ()

        #self.infobar = Gtk.InfoBar ()
        #self.box.pack_start (self.infobar, 0, 0, 0)

        box1.pack_start (box2, 1, 0, 0)
        box2.pack_start (self.image_event_box, 0, 0, 0)
        
        self.image_sw.add (box1)
        self.image_sw.set_policy (Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.image_sw.set_min_content_width (640)
        self.image_sw.set_min_content_height (310)
        
        self.paned = Gtk.VPaned ()
        self.image_revealer.add (self.image_sw)
        self.paned.pack1 (self.image_revealer, resize = True, shrink = True)

        self.overlay = Gtk.Overlay ()
        self.overlay.add (self.paned)
        
        self.box.pack_start (self.overlay, 1, 1, 0)
    
        self.logofy ()
        
        self.text_view = Gtk.TextView ()
        self.text_view.set_cursor_visible (False)
        
        self.text_buffer = self.text_view.get_buffer ()

        #self.text_buffer.set_text ("Welcome")

        pango_font = Pango.FontDescription.from_string ("Ubuntu Mono 35")
        self.text_view.set_pixels_below_lines (7)
        self.text_view.modify_font (pango_font)
        self.modify_font (pango_font)
      
        self.text_tags = []
        for tag in TextAttributeTags:
            #print (tag [0], tag [1], tag [2])
            self.text_tags.append (self.text_buffer.create_tag (tag_name = tag [0],
                                    foreground = tag [1],
                                    weight = tag [2]))
            self.text_tags.append (self.text_buffer.create_tag (tag_name = tag [0] + "-error",
                                    foreground = tag [1],
                                    weight = tag [2], background = "yellow")) #red3


        self.text_view_sw = Gtk.ScrolledWindow ()
        self.text_view_sw.add (self.text_view)
        self.text_view_sw.set_policy (Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.text_view_revealer = Gtk.Revealer ()
        self.text_view_revealer.set_reveal_child (True)
        self.text_view_revealer.set_transition_type (4)

        self.notebook = Gtk.Notebook ()
        self.play_button = Gtk.ToggleButton ()
        self.play_button.set_active (True)
        self.play_button.set_sensitive (True)
        #icons = self.icon_theme.list_icons ()
        #icons. sort ()
        #print (icons)
        self.play_button.set_image (Gtk.Image.new_from_pixbuf (self.icon_theme.load_icon ('media-playback-start', 48, Gtk.IconLookupFlags.GENERIC_FALLBACK)))
        self.play_button.show_all ()
        #self.play_button.set_relief (Gtk.ReliefStyle.NONE)
        #self.play_button.connect ('toggled', lambda *w: self.unpause_camera () if self.play_button.get_active () else self.pause_camera ())
        self.notebook.set_action_widget (self.play_button, 1)
        self.notebook.append_page (self.text_view_sw, Gtk.Label ('Console'))

        self.text_view_revealer.add (self.notebook)
        self.paned.pack2 (self.text_view_revealer, resize = True, shrink = False)
        self.text_view.set_editable (False)
        
        self.entry = Gtk.Entry ()
        self.entry.modify_font (pango_font)
        self.button_box = Gtk.HBox ()
        self.button_box_revealer = Gtk.Revealer ()
        self.button_box_revealer.set_reveal_child (True)

        self.button_box_revealer.add (self.button_box)
        self.button_box_revealer.set_transition_type (4)
        self.box.pack_start (self.button_box_revealer, 0, 0, 10)

        self.text_view_sw.set_min_content_width (1000)
        self.text_view_sw.set_min_content_height (200)
        self.text_view_sw.set_can_focus (False)
        self.text_view.set_can_focus (False)
        self.text_view.set_wrap_mode (Gtk.WrapMode.WORD_CHAR)
        
        bg_color = Gdk.RGBA ()
        bg_color.parse ("#F1F1F1")
        self.text_view.override_background_color (0, bg_color)
        
        self.entry.connect ("activate", self.entry_activate)
        #self.entry.connect ("activate", lambda self: self.set_text (""))

        self.entry_completion_store = Gtk.ListStore (str)
        self.entry_completion = Gtk.EntryCompletion ()

        #self.entry_completion.connect ('cursor-on-match', lambda *w: self.entry.select_region (-1, -1))
        
        self.entry_completion.set_model (self.entry_completion_store)
        self.entry.set_completion (self.entry_completion)
        
        self.entry_completion.set_inline_completion (True)
        #self.entry_completion.set_popup_completion (False)
        self.entry_completion.set_inline_selection (True)
        self.entry_completion.set_text_column (0)
        self.entry_completion.set_minimum_key_length (2)
        
        self.hasher.append ("bridge-start", self.bridge_input_start_hook)
        self.hasher.append ("bridge-list", lambda *w: self.bridge_list_ui ())
        self.hasher.append ("bridge-current-id", lambda *w: self.bridge_current_id ())
        self.hasher.append ("print", self.print_input)
        self.hasher.append ("camera-start", self.start_camera)
        self.hasher.append ("camera-stop", self.stop_camera)
        self.hasher.append ("picture-load", self.picture_load)
        self.hasher.append ("picture-folder-load", self.gallery_open)
        self.hasher.append ("video-start", self.start_video)
        self.hasher.append ("video-stop", self.stop_video)
        self.hasher.append ("picture-unload", self.stop_video)
        self.hasher.append ("video-pause", self.pause_camera)
        self.hasher.append ("video-unpause", self.unpause_camera)
        self.hasher.append ("camera-pause", self.pause_camera)
        self.hasher.append ("camera-unpause", self.unpause_camera)
        self.hasher.append ("camera-screenshot", self.screenshot)
        self.hasher.append ("video-seek", self.seek_video)
        self.hasher.append ("clear", self.text_view_clear)
        self.hasher.append ("zoom-in", self.zoom_in)
        self.hasher.append ("zoom-out", self.zoom_out)
        self.hasher.append ("zoom-fit", self.zoom_fit)
        self.hasher.append ("zoom-100", self.zoom_100)
        self.hasher.append ("focus-on", lambda self: self.ui.focus_toggle (True))
        self.hasher.append ("focus-off", lambda self: self.ui.focus_toggle ())
        self.hasher.append ("focus-get", lambda self: self.ui.camera_show_focus ())
        self.hasher.append ("focus-mode-color", lambda self: self.ui.set_focus_mode (mode = FocusMode.color))
        self.hasher.append ("focus-mode-contour", lambda self: self.ui.set_focus_mode (mode = FocusMode.contour))
        self.hasher.append ("help-shortcuts", lambda self: self.ui.keyboard_shortcuts ())
        #self.hasher.append ("cog-data-sources", lambda self: self.ui.cog.list_data_sources ())
        #self.hasher.append ("cog-input-sources", lambda self: self.ui.cog.list_input_sources ())
        
        self.hasher.append ('app-db-browser', lambda self, *w: zodb_browser ())
        self.hasher.append ('app-xkcd-browser', lambda self, *w: xkcd_browser ())
        self.hasher.append ("app-generate-contour", lambda selfie, *w: self.peep_contour ())

        self.hasher.append ('focus-print-selection', lambda self, *w: self.ui.print_selection ())
        self.hasher.append ('focus-select-all', lambda self, *w: self.ui.set_selection_all ())
        self.hasher.append ('focus-selection-to-cluster', lambda *w: self.contourfocus.selection_to_clusters ())
        self.hasher.append ('focus-clusters-generate', lambda *w: self.contourfocus.generate_contour_clusters ())
        self.hasher.append ('focus-append-selection-to-cluster', lambda *w: self.contourfocus.append_selection_to_clusters ())
        self.hasher.append ('introspect', self.introspect)
        self.hasher.append ('focus-range-select', lambda *w: self.set_selection_range_hook ())
        self.hasher.append ('focus-auto-select-cluster', lambda *w: self.contourfocus.selection_auto_select_cluster ())
        self.hasher.append ('focus-auto-select-generated-cluster', lambda *w: self.contourfocus.selection_auto_select_generated_cluster ())
        self.hasher.append ('image-save', lambda *w: self.save_current_frame ())
        self.hasher.append ('canvas-new', lambda *w: self.canvas_new_image ())
        self.hasher.append ('canvas-line', lambda *w: self.canvas_draw_line ())
        self.hasher.append ('canvas-clear', lambda *w: self.canvas_clear ())
        self.hasher.append ('canvas-paint', lambda *w: self.canvas_clear (choose_color = True))
        self.hasher.append ('canvas-circle', lambda *w: self.canvas_draw_circle ())
        self.hasher.append ('canvas-rectangle', lambda *w: self.canvas_draw_rect ())
        self.hasher.append ('canvas-text', lambda *w: self.canvas_draw_text ())
        
        self.menu_button = Gtk.MenuButton ()
        self.menu_button.set_can_focus (False)
        bp = GdkPixbuf.Pixbuf.new_from_file_at_scale ("ui-resources/icon-small.png", 64, 64, 0)

        self.abort = Gtk.ToggleButton ()
        self.abort.add (Gtk.Image.new_from_icon_name ('stop', 64))
        
        self.abort.show_all ()
        self.abort.set_no_show_all (True)
        self.abort.hide ()
        
        self.menu_button.set_image (Gtk.Image.new_from_pixbuf (bp))
        self.button_box.pack_start (self.menu_button, 0, 0, 10)
        self.button_box.pack_start (self.entry, 1, 1, 5)
        self.button_box.pack_start (self.abort, 0, 0, 10)

        self.contour = Gtk.Grid ()
        self.contour.set_column_spacing (20)
        self.contour.set_row_spacing (20)

        self.contour.sw = Gtk.ScrolledWindow ()
        self.contour.sw.add (self.contour)
        
        self.contour.spin1 = Gtk.SpinButton.new_with_range (1.0, 1000.0, 1.0)        
        self.contour.spin2 = Gtk.SpinButton.new_with_range (1.0, 1000.0, 1.0)        
        self.contour.select_from = Gtk.SpinButton.new_with_range (-1.0, 1000.0, 1.0)
        self.contour.select_to = Gtk.SpinButton.new_with_range (-1.0, 1000.0, 1.0)        
        self.contour.select_cluster = Gtk.SpinButton.new_with_range (-1, 1000.0, 1.0)
        self.contour.thickness = Gtk.SpinButton.new_with_range (-5.0, 10.0, 1.0)        
        self.contour.selection = Gtk.SpinButton.new_with_range (0.0, 100.0, 1.0)        
        self.contour.flip_axis = Gtk.SpinButton.new_with_range (-1, 1.0, 1.0)        
        self.contour.flip = Gtk.CheckButton.new_with_label ('Flip')
        
        self.contour.canny_mode = Gtk.ComboBoxText ()
        self.contour.canny_method = Gtk.ComboBoxText ()

        self.contour.color = Gtk.ColorButton ()
        self.contour.es_color = Gtk.ColorButton ()
        
        self.contour.draw_all = Gtk.CheckButton.new_with_label ('All')
        self.contour.draw_only = Gtk.CheckButton.new_with_label ('Only')

        self.contour.randomize = Gtk.CheckButton.new_with_label ('Random')
        self.contour.randomize.ui = self
        self.contour.color.ui = self
        self.contour.es_color.ui = self

        self.contour.draw_only.ui = self
        self.contour.draw_all.ui = self

        self.contour.mode = Gtk.ComboBoxText ()
        for mode in FocusMode:
            #if mode.value:
            self.contour.mode.insert (mode.value, mode.name, mode.name)
        
        self.contour.attach (self.contour.draw_all, 2, 0, 2, 1)
        self.contour.attach (self.contour.randomize, 4, 0, 1, 1)
        self.contour.attach (Gtk.Label ('Focus'), 4, 1, 1, 1)
        self.contour.attach (self.contour.mode, 5, 1, 3, 1)
        self.contour.attach (self.contour.color, 5, 2, 1, 1)
        self.contour.attach (self.contour.es_color, 6, 2, 1, 1)
        self.contour.attach (self.contour.flip, 7, 2, 1, 1)
        self.contour.attach (self.contour.thickness, 5, 0, 1, 1)
        self.contour.attach (self.contour.selection, 6, 0, 1, 1)
        self.contour.attach (self.contour.select_from, 7, 0, 1, 1)
        self.contour.attach (self.contour.select_to, 8, 0, 1, 1)
        self.contour.attach (self.contour.select_cluster, 8, 1, 1, 1)
        self.contour.attach (self.contour.flip_axis, 8, 2, 1, 1)
        self.contour.attach (self.contour.draw_only, 2, 1, 2, 1)
    
        self.contour.draw_only.connect ('toggled', lambda self, *w: self.ui.contourfocus.setattr ('draw_only_contours', self.get_active ()))
        self.contour.draw_all.connect ('toggled', lambda self, *w: self.ui.contourfocus.setattr ('draw_all_contours', self.get_active ()))
        
        self.contour.canny_mode.connect ('changed', lambda self, *w: self.ui.contourfocus.setattr ('mode', self.get_active ()))
        self.contour.canny_method.connect ('changed', lambda self, *w: self.ui.contourfocus.setattr ('method', self.ui.contourfocus.CannyMethods [self.get_active_text ()].value))
        
        self.contour.color.connect ('color-set', lambda self, *w: self.ui.contourfocus.setattr ('selection_color', (self.get_rgba ().blue * 255, self.get_rgba ().green * 255, self.get_rgba ().red * 255)))
        self.contour.es_color.connect ('color-set', lambda self, *w: self.ui.contourfocus.setattr ('es_color', (self.get_rgba ().blue * 255, self.get_rgba ().green * 255, self.get_rgba ().red * 255)))
                
        self.contour.mode.connect ('changed', lambda self, *w: self.ui.set_focus_mode (self.get_active ()))
        self.contour.randomize.connect ('toggled', lambda self, *w: self.ui.contourfocus.setattr ('randomize', self.get_active ()))
        self.contour.flip.connect ('toggled', lambda *w: self.contourfocus.setattr ('flip', self.contour.flip.get_active ()))
        #self.contour.spin2.set_value (200)

        self.contour.select_from.connect ('changed', lambda *w: self.set_selection_range_from_spin ())
        self.contour.select_to.connect ('changed', lambda *w: self.set_selection_range_from_spin ())
        self.contour.select_cluster.connect ('changed', lambda *w: self.contourfocus.select_cluster (self.contour.select_cluster.get_value_as_int () if len (self.contourfocus.clusters) > 0 and self.contour.select_cluster.get_value_as_int () < len (self.contourfocus.clusters) else None))#self.contour.select_cluster.set_range (-1, len (self.contourfocus.clusters) + 1)))
        self.contour.select_cluster.connect ('changed', lambda *w: self.contour.select_cluster.set_range (-1, len (self.contourfocus.clusters) + 1))
    
        self.contour.mode.ui = self
        self.contour.spin1.ui = self
        self.contour.spin2.ui = self
        self.contour.thickness.ui = self
        self.contour.selection.ui = self
        self.contour.canny_method.ui = self
        self.contour.canny_mode.ui = self

        self.contour.mode.set_tooltip_text ('Contour mode')
        self.contour.spin1.set_tooltip_text ('Canny Threshold 1')
        self.contour.spin2.set_tooltip_text ('Canny Threshold 2')
        self.contour.thickness.set_tooltip_text ('Thickness')
        self.contour.selection.set_tooltip_text ('Selection')
        self.contour.canny_method.set_tooltip_text ('Canny Method')
        self.contour.canny_mode.set_tooltip_text ('Canny Mode')
        self.contour.flip.set_tooltip_text ('Flip')
        self.contour.select_from.set_tooltip_text ('Select from')
        self.contour.select_to.set_tooltip_text ('Select to')
        self.contour.flip_axis.set_tooltip_text ('Flip axis')
        self.contour.draw_only.set_tooltip_text ('Draw only contours')
        self.contour.draw_all.set_tooltip_text ('Draw all contours')
        self.contour.randomize.set_tooltip_text ('Randomize colors')
        self.contour.select_cluster.set_tooltip_text ('Select contour cluster')
    
        self.contour.spin1.connect ('value-changed', lambda self, *w: self.ui.contourfocus.setattr ('canny1', self.get_value_as_int ()))
        self.contour.spin2.connect ('value-changed', lambda self, *w: self.ui.contourfocus.setattr ('canny2', self.get_value_as_int ()))
        self.contour.flip_axis.connect ('value-changed', lambda *w: self.contourfocus.setattr ('flip_axis', self.contour.flip_axis.get_value_as_int ()))
        self.contour.thickness.connect ('value-changed', lambda self, *w: self.ui.contourfocus.setattr ('thickness', self.get_value_as_int ()))
        self.contour.selection.connect ('value-changed', self.set_selection)
        #self.contour.spin2.connect ('value-changed', lambda self, *w: self.ui.contour_update ())
    
        self.contour.attach (Gtk.Label ('C 1'), 0, 0, 1, 1)
        self.contour.attach (self.contour.spin1, 1, 0, 1, 1)
        self.contour.attach (Gtk.Label ('C 2'), 0, 1, 1, 1)
        self.contour.attach (self.contour.spin2, 1, 1, 1, 1)
        self.contour.attach (self.contour.canny_mode, 0, 2, 2, 1)
        self.contour.attach (self.contour.canny_method, 2, 2, 3, 1)
    
        self.contour.vbox = Gtk.VBox ()
        self.contour.hbox = Gtk.HBox ()
        
        self.contour.vbox.pack_start (self.contour.sw, 1, 1, 10)
        self.contour.hbox.pack_start (self.contour.vbox, 1, 1, 10)
        
        self.notebook.append_page (self.contour.hbox, Gtk.Label ('Contours'))

        # Processing
        self.proc = Gtk.Notebook ()
        
        self.dfilters = Gtk.Grid ()
        self.dfilters.sw = Gtk.ScrolledWindow ()
        self.dfilters.hbox = Gtk.HBox ()
        self.dfilters.sw.add (self.dfilters.hbox)
        self.dfilters.set_column_spacing (10)
        self.dfilters.set_row_spacing (10)
        self.dfilters.vbox = Gtk.VBox ()
        self.dfilters.hbox.pack_start (self.dfilters.vbox, 1, 1, 10)
        self.dfilters.vbox.pack_start (self.dfilters, 1, 1, 10)
        
        gax = gay = 0
        
        for i in self.filter_host.filters:
            fax = 0
            fay = 1
            # check button with name at 0, 0
            
            opts = self.filter_host.filters [i].getopts ()
            
            if len (opts) == 0:
                continue
            
            g = Gtk.Grid ()
            g.set_row_spacing (20)
            g.set_column_spacing (20)
            cb = Gtk.CheckButton.new_with_label (self.filter_host.filters [i].name)
            g . attach (cb, 0, 0, 4, 1)
            self.filter_host.filters [i].enabled = cb

            for o in opts:
                if len (o) == 0:
                    continue
                
                if o [0] == int:
                    sb = Gtk.SpinButton.new_with_range (o [2], o [3], o [4])
                    sb.set_value (o [-1])
                    sb.set_tooltip_text (o [1])
                    setattr (sb, "filter", i)
                    sb.connect ("value-changed", lambda *w: setattr (self.filter_host.filters [getattr (w [0], "filter")], w [0].get_tooltip_text (), w [0].get_value_as_int ()))
                    #sb.connect ("value-changed", lambda *w:  print (getattr (w [0], "filter")))
                    #l = Gtk.Label (o [1])
                    #g.attach (l, fax, fay, 1, 1)
                    
                    fax += 1
                    g.attach (sb, fax, fay, 1, 1)
                    #fay += 1
                    #fax -= 1
                    if fax >= 3:
                        fax = 0
                        fay += 1
                        
            self.dfilters.attach (g, gax, gay, 1, 1)
            gax += 1
            
            if gax >= 3:
                gay += 1
                gax = 0
        
        
        self.filters = Gtk.Grid ()
        self.filters.sw = Gtk.ScrolledWindow ()
        self.filters.hbox = Gtk.HBox ()
        self.filters.sw.add (self.filters.hbox)
        self.filters.set_column_spacing (10)
        self.filters.set_row_spacing (10)
        self.filters.vbox = Gtk.VBox ()
        self.filters.hbox.pack_start (self.filters.vbox, 1, 1, 10)
        self.filters.vbox.pack_start (self.filters, 1, 1, 10)

        self.filters.scale = Gtk.CheckButton.new_with_label ('Scale')
        self.filters.scale.width = Gtk.SpinButton.new_with_range (0, 5000, 1)
        self.filters.scale.height = Gtk.SpinButton.new_with_range (0, 5000, 1)
        
        self.filters.scale.connect ('toggled', lambda *w: self.__reset_scale__ () if not self.filters.scale.width.get_value_as_int () or not self.filters.scale.height.get_value_as_int () else True)

        self.filters.scale.width.set_tooltip_text ('Scale width')
        self.filters.scale.height.set_tooltip_text ('Scale height')

        self.filters.rotate = Gtk.CheckButton.new_with_label ('Rotate')
        self.filters.rotate.angle = Gtk.SpinButton.new_with_range (-180, 180, 1)
        self.filters.rotate.angle.set_value (0)
        self.filters.rotate.angle.set_tooltip_text ('Rotate angle')

        self.filters.zoom = Gtk.CheckButton.new_with_label ('Zoom')
        self.filters.zoom.value = Gtk.SpinButton.new_with_range (0, 180, 1)
        
        self.filters.zoom.x1 = Gtk.CheckButton.new_with_label ('x1')
        self.filters.zoom.y1 = Gtk.CheckButton.new_with_label ('y1')
        self.filters.zoom.x2 = Gtk.CheckButton.new_with_label ('x2')
        self.filters.zoom.y2 = Gtk.CheckButton.new_with_label ('y2')
        self.filters.zoom.x3 = Gtk.CheckButton.new_with_label ('x3')
        self.filters.zoom.y3 = Gtk.CheckButton.new_with_label ('y3')
        self.filters.zoom.x4 = Gtk.CheckButton.new_with_label ('x4')
        self.filters.zoom.y4 = Gtk.CheckButton.new_with_label ('y4')
        
        self.sleep_spin = Gtk.SpinButton.new_with_range (10, 10000, 1)
        self.sleep_spin.set_sensitive (False)
        self.sleep_spin.set_value (self.sleep_interval)
        self.sleep_spin.set_tooltip_text ('Main loop delay interval')
        self.sleep_spin.connect ('value-changed', lambda *w: self.sleep_interval_set ())
        self.filters.attach (self.filters.scale, 0, 0, 2, 1)
        self.filters.attach (self.filters.scale.width, 0, 1, 1, 1)
        self.filters.attach (self.filters.scale.height, 0, 2, 1, 1)
        self.filters.attach (Gtk.VSeparator (), 3, 0, 1, 3)
        self.filters.attach (Gtk.VSeparator (), 5, 0, 1, 3)
        self.filters.attach (self.filters.rotate, 4, 0, 1, 1)
        self.filters.attach (self.filters.rotate.angle, 4, 1, 1, 1)
        self.filters.attach (self.filters.zoom, 6, 0, 2, 1)
        self.filters.attach (self.filters.zoom.value, 8, 0, 2, 1)
        self.filters.attach (self.filters.zoom.x1, 6, 1, 1, 1)
        self.filters.attach (self.filters.zoom.y1, 6, 2, 1, 1)
        self.filters.attach (self.filters.zoom.x2, 7, 1, 1, 1)
        self.filters.attach (self.filters.zoom.y2, 7, 2, 1, 1)
        self.filters.attach (self.filters.zoom.x3, 8, 1, 1, 1)
        self.filters.attach (self.filters.zoom.y3, 8, 2, 1, 1)
        self.filters.attach (self.filters.zoom.x4, 9, 1, 1, 1)
        self.filters.attach (self.filters.zoom.y4, 9, 2, 1, 1)
        self.filters.attach (Gtk.VSeparator (), 10, 0, 1, 3)
        self.filters.attach (Gtk.Label ('Sleep'), 11, 0, 1, 1)
        self.filters.attach (self.sleep_spin, 11, 1, 1, 1)
        
        self.blur = Gtk.Grid ()
        self.blur.sw = Gtk.ScrolledWindow ()
        self.blur.sw.add (self.blur)
        self.blur.hbox = Gtk.HBox ()
        self.blur.vbox = Gtk.VBox ()
        self.blur.vbox.pack_start (self.blur.sw, 1, 1, 10)
        self.blur.hbox.pack_start (self.blur.vbox, 1, 1, 10)
        self.blur.set_column_spacing (10)
        self.blur.set_row_spacing (10)
        
        # cv2.blur ()
        self.blur.simple = Gtk.Switch ()
        self.blur.simple.ksize = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.blur.simple.ksize.set_tooltip_text ('Blurring kernel size')

        self.blur.box = Gtk.Switch ()
        self.blur.box.normalize = Gtk.CheckButton.new_with_label (' Kn')
        self.blur.box.normalize.set_tooltip_text ('Normalize kernel')
        self.blur.box.ksize = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.blur.box.ksize.set_tooltip_text ('Blurring kernel size')
        
        self.blur.dilate = Gtk.Switch ()
        self.blur.dilate.erode = Gtk.CheckButton.new_with_label ('Erode')
        self.blur.dilate.shape = Gtk.SpinButton.new_with_range (0,100,1)
        self.blur.dilate.ksize = Gtk.SpinButton.new_with_range (0,100,1)
        self.blur.dilate.iterations = Gtk.SpinButton.new_with_range (0,100,1)
        self.blur.dilate.iterations.set_tooltip_text ('Iterations')
        self.blur.dilate.shape.set_tooltip_text ('Shape')
        self.blur.dilate.ksize.set_tooltip_text ('Kernel size')
        
        self.blur.gaussian = Gtk.Switch ()
        self.blur.gaussian.ksize = Gtk.SpinButton.new_with_range (0,100,1)
        self.blur.gaussian.sigmax = Gtk.SpinButton.new_with_range (0,100,1)
        self.blur.gaussian.sigmay = Gtk.SpinButton.new_with_range (0,100,1)
        self.blur.gaussian.ksize.set_tooltip_text ('Kernel size')
        self.blur.gaussian.sigmax.set_tooltip_text ('Gaussian kernel standard deviation in X direction')
        self.blur.gaussian.sigmay.set_tooltip_text ('Gaussian kernel standard deviation in Y direction')
        
        self.blur.median = Gtk.Switch ()
        self.blur.median.ksize = Gtk.SpinButton.new_with_range (0,100,1)
        self.blur.median.ksize.set_tooltip_text ('Kernel size')
        
        self.blur.bil = Gtk.Switch ()
        self.blur.bil.d = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.blur.bil.sigma_color = Gtk.SpinButton.new_with_range (0, 500, 1)
        self.blur.bil.sigma_space = Gtk.SpinButton.new_with_range (0, 500, 1)
        self.blur.bil.d.set_tooltip_text ('Diameter of each pixel neighborhood that is used during filtering')
        self.blur.bil.sigma_color.set_tooltip_text ('Filter sigma in the color space. A larger value of the parameter means that\nfarther colors within the pixel neighborhood (see sigmaSpace ) will be mixed together, resulting in larger areas of semi-equal color')
        self.blur.bil.sigma_space.set_tooltip_text ('Filter sigma in the coordinate space. A larger value of the parameter means\nthat farther pixels will influence each other as long as their colors are close enough')

        self.proc.append_page (self.filters.sw, Gtk.Label ('Transform'))
        self.proc.append_page (self.blur.hbox, Gtk.Label ('Blur'))
        
        self.blur.attach (Gtk.Label ('Median'), 0, 0, 1, 1) 
        self.blur.attach (self.blur.median, 1, 0, 1, 1)
        self.blur.attach (self.blur.median.ksize, 1, 1, 1, 1)
        self.blur.attach (Gtk.VSeparator (), 2, 0, 1, 3)
        self.blur.attach (Gtk.Label ('Gaussian'), 3, 0, 1, 1)
        self.blur.attach (self.blur.gaussian, 4, 0, 1, 1)
        self.blur.attach (self.blur.gaussian.ksize, 3, 2, 1, 1)
        self.blur.attach (self.blur.gaussian.sigmax, 3, 1, 1, 1)
        self.blur.attach (self.blur.gaussian.sigmay, 4, 1, 1, 1)
        self.blur.attach (Gtk.VSeparator (), 5, 0, 1, 3)
        self.blur.attach (Gtk.Label ('Box'), 6, 0, 1, 1)
        self.blur.attach (self.blur.box, 7, 0, 1, 1)
        self.blur.attach (self.blur.box.ksize, 7, 1, 1, 1)
        self.blur.attach (self.blur.box.normalize, 6, 1, 1, 1)
        
        self.blur.attach (Gtk.VSeparator (), 8, 0, 1, 3)
        self.blur.attach (Gtk.Label ('Simple'), 9, 0, 1, 1)
        self.blur.attach (self.blur.simple, 10, 0, 1, 1)
        self.blur.attach (self.blur.simple.ksize, 10, 1, 1, 1)
        
        self.blur.attach (Gtk.HSeparator (), 0, 4, 10, 1)
        self.blur.attach (Gtk.Label ('Dilate'), 0, 5, 1, 1)
        self.blur.attach (self.blur.dilate, 1, 5, 1, 1)
        self.blur.attach (self.blur.dilate.ksize, 0, 6, 1, 1)
        self.blur.attach (self.blur.dilate.shape, 1, 6, 1, 1)
        self.blur.attach (self.blur.dilate.iterations, 3, 6, 1, 1)
        self.blur.attach (Gtk.VSeparator (), 5, 4, 1, 3)
        self.blur.attach (Gtk.Label ('Bilateral'), 6, 5, 2, 1)
        self.blur.attach (self.blur.bil, 9, 5, 1, 1)
        self.blur.attach (self.blur.bil.d, 9, 6, 1, 1)
        self.blur.attach (self.blur.bil.sigma_color, 10, 5, 1, 1)
        self.blur.attach (self.blur.bil.sigma_space, 10, 6, 1, 1)
        

        self.gallery = Gtk.IconView ()
        self.gallery.connect ('key-press-event', self.gallery_search)
        self.gallery.set_text_column (-1)
        self.gallery.set_pixbuf_column (0)
        self.gallery.connect ('item-activated', self.gallery_item_activated)
        self.gallery.store = Gtk.ListStore (GdkPixbuf.Pixbuf, str, str)
        self.gallery.store.set_sort_column_id (1, 0)
        self.gallery.sw = Gtk.ScrolledWindow ()
        self.gallery.sw.set_vexpand (True)
        self.gallery.sw.set_hexpand (True)
        self.gallery.store.set_sort_column_id (1, 0)
        self.gallery.set_model (self.gallery.store)
        self.gallery.sw.add (self.gallery)
        self.gallery.grid = Gtk.Grid ()
        self.gallery.grid.attach (self.gallery.sw, 0, 0, 1, 1)
        
        self.gallery.search = Gtk.Popover.new (self.play_button)
        self.gallery.search.bar = Gtk.SearchBar ()
        self.gallery.search.entry  = Gtk.SearchEntry ()
        self.gallery.search.bar.add (self.gallery.search.entry)
        self.gallery.search.add (self.gallery.search.bar)
        self.gallery.search.entry.connect ('changed', lambda *w: self.gallery_do_search_like_fo_real (self.gallery.search.entry.get_text ()))
        self.gallery.search.entry.connect ('activate', lambda *w: self.gallery_do_search_like_fo_real (self.gallery.search.popdown ()))
        self.gallery.search.entry.connect ('activate', lambda *w: self.gallery_item_activated (self.gallery, None))
        
        self.gallery.search.bar.set_show_close_button (True)
        self.gallery.search.bar.set_search_mode (True)
        self.gallery.search.connect ('closed', lambda *w: self.gallery.grab_focus ())
        
        self.fast = Gtk.Grid ()
        self.fast.hbox = Gtk.HBox ()
        self.fast.vbox = Gtk.VBox ()
        
        self.fast.vbox.pack_start (self.fast, 1, 1, 10)
        self.fast.hbox.pack_start (self.fast.vbox, 1, 1, 10)
        
        self.fast.set_column_spacing (20)
        self.fast.set_row_spacing (20)
        self.fast.threshold = Gtk.SpinButton.new_with_range (0, 100, 1.0)
        self.fast.nms = Gtk.Switch ()
        self.fast.type = Gtk.ComboBoxText ()
        self.fast.draw_only_key_points = Gtk.Switch ()
        fast_title = Gtk.Label ('Features from accelerated segment')
        fast_title.set_markup ('<b>Features from accelerated segment</b>')
        fast_title.set_sensitive (False)
        fast_title.set_justify (0)
        #self.fast.attach (fast_title, 0, 0, 4, 1)
        self.fast.attach (Gtk.Label ('Threshold'), 0, 1, 1, 1)
        self.fast.attach (self.fast.threshold, 1, 1, 1, 1)
        self.fast.attach (Gtk.Label ('Non Max'), 0, 3, 1, 1)
        self.fast.attach (self.fast.nms, 1, 3, 1, 1)
        self.fast.attach (Gtk.Label ('Only'), 2, 3, 1, 1)
        self.fast.attach (self.fast.draw_only_key_points, 3, 3, 1, 1)
        self.fast.attach (Gtk.Label ('Type'), 2, 1, 1, 1)
        self.fast.attach (self.fast.type, 3, 1, 2, 1)
    
        self.orb = Gtk.Grid ()
        
        self.orb.edge_threshold = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.orb.fast_threshold = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.orb.first_level = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.orb.max_features = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.orb.n_levels = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.orb.patch_size = Gtk.SpinButton.new_with_range (0, 100, 1)
        self.orb.scale_factor = Gtk.SpinButton.new_with_range (0, 100, .1)
        self.orb.score_type = Gtk.SpinButton.new_with_range (0, 100, 1)

        self.orb.edge_threshold.set_tooltip_text ('Edge Threshold')
        self.orb.fast_threshold.set_tooltip_text ('Fast Threshold')
        self.orb.first_level.set_tooltip_text ('First level')
        self.orb.max_features.set_tooltip_text ('Max features')
        self.orb.n_levels.set_tooltip_text ('N Levels')
        self.orb.patch_size.set_tooltip_text ('Patch size')
        self.orb.scale_factor.set_tooltip_text ('Scale factor')
        self.orb.score_type.set_tooltip_text ('Score type')

        self.orb.hdeco = Gtk.HSeparator ()
        self.orb.vdeco = Gtk.VSeparator ()

        self.orb.attach (self.orb.hdeco, 0, 0, 1, 1)
        self.orb.attach (Gtk.Label ('Edge'), 1, 1, 1, 1)
        self.orb.attach (self.orb.edge_threshold, 2, 1, 1, 1)
        self.orb.attach (Gtk.Label ('Fast'), 1, 2, 1, 1)
        self.orb.attach (self.orb.fast_threshold, 2, 2, 1, 1)
        self.orb.attach (Gtk.Label ('First'), 3, 1, 1, 1)
        self.orb.attach (self.orb.first_level, 4, 1, 1, 1)
        self.orb.attach (Gtk.Label ('Max'), 3, 2, 1, 1)
        self.orb.attach (self.orb.max_features, 4, 2, 1, 1)
        
        self.orb.attach (Gtk.Label ('Levels'), 5, 1, 1, 1)
        self.orb.attach (self.orb.n_levels, 6, 1, 1, 1)
        self.orb.attach (Gtk.Label ('Patch'), 5, 2, 1, 1)
        self.orb.attach (self.orb.patch_size, 6, 2, 1, 1)
        self.orb.attach (Gtk.Label ('Scale'), 7, 1, 1, 1)
        self.orb.attach (self.orb.scale_factor, 8, 1, 1, 1)
        self.orb.attach (Gtk.Label ('Score'), 7, 2, 1, 1)
        self.orb.attach (self.orb.score_type, 8, 2, 1, 1)
        
        self.orb.set_column_spacing (20)
        self.orb.set_row_spacing (20)

        self.orb.edge_threshold.connect ('changed', lambda *w: self.orbfocus.orb.setEdgeThreshold (self.orb.edge_threshold.get_value_as_int ()))
        self.orb.fast_threshold.connect ('changed', lambda *w: self.orbfocus.orb.setFastThreshold (self.orb.fast_threshold.get_value_as_int ()))
        self.orb.first_level.connect ('changed', lambda *w: self.orbfocus.orb.setFirstLevel (self.orb.first_level.get_value_as_int ()))
        self.orb.max_features.connect ('changed', lambda *w: self.orbfocus.orb.setMaxFeatures (self.orb.max_features.get_value_as_int ()))
        self.orb.n_levels.connect ('changed', lambda *w: self.orbfocus.orb.setNLevels (self.orb.n_levels.get_value_as_int ()))
        self.orb.patch_size.connect ('changed', lambda *w: self.orbfocus.orb.setPatchSize (self.orb.patch_size.get_value_as_int ()))
        self.orb.scale_factor.connect ('changed', lambda *w: self.orbfocus.orb.setScaleFactor (self.orb.scale_factor.get_value ()))
        self.orb.score_type.connect ('changed', lambda *w: self.orbfocus.orb.setScoreType (self.orb.score_type.get_value_as_int ()))

        self.fast.threshold.connect ('changed', lambda *w: self.fastfocus.set (threshold = self.fast.threshold.get_value_as_int ()))
        self.fast.nms.connect ('state-set', lambda *w: self.fastfocus.set (nms = self.fast.nms.get_active ()))
        self.fast.type.connect ('changed', lambda *w: self.fastfocus.set (ftype = self.fast.type.get_active ()))
        self.fast.draw_only_key_points.connect ('state-set', lambda *w: self.fastfocus.set (draw_only_key_points = self.fast.draw_only_key_points.get_active ()))

        self.fast.sw = Gtk.ScrolledWindow ()
        self.fast.sw.add (self.fast.hbox)

        self.orb.sw = Gtk.ScrolledWindow ()
        self.orb.sw.add (self.orb)

        self.features = Gtk.Notebook ()

        self.features.append_page (self.fast.sw, Gtk.Label ('Fast'))
        self.features.append_page (self.orb.sw, Gtk.Label ('ORB'))
        
        self.notebook.append_page (self.features, Gtk.Label ('Features'))
        self.notebook.append_page (self.proc, Gtk.Label ('Transform'))
        self.notebook.append_page (self.dfilters.sw, Gtk.Label ('Filters'))
        self.notebook.append_page (self.gallery.grid, Gtk.Label ("Gallery"))

        self.menu = Gtk.Menu ()
        menu_title = Gtk.MenuItem.new_with_label ("Menu")
        self.menu.append (menu_title)
        self.menu.append (Gtk.SeparatorMenuItem ())
        menu_title.set_sensitive (False)

        menuitems = dict ()

        mnemonics_root = []
        mnemonics = []

        for command in self.hasher.commands:
            self.entry_completion_store.set_value (self.entry_completion_store.append (), 0, "#" + command)
            if len (command) < 1:
                continue
            
            item = None
            if "-" in command:
                v = command.split ("-", maxsplit = 1)
                menu_label = v [1].title ()
                menu_label = self.menu_item_set_mnemonic (menu_label)
                #m = menu_label [0]
                #for m in menu_label:
                    #if m in mnemonics:
                        #continue
                    #else:
                        #mnemonics.append (m)
                        #break
                
                #menu_label = menu_label.replace (m, '_' + m, 1)
                #print (m,menu_label)
                #item = Gtk.MenuItem.new_with_mnemonic ("_" + v [1][:1].upper () + v [1][1:])
                item = Gtk.MenuItem.new_with_mnemonic (menu_label)
                if v [0] not in menuitems:
                    shell = Gtk.Menu ()
                    #shellitem = Gtk.MenuItem.new_with_mnemonic ("_" + v[0][:1].upper () + v[0][1:])
                    menu_label = v [0].title ()
                    menu_label = self.menu_item_set_mnemonic (menu_label)
                    #m = menu_label [0]
                    #for m in menu_label:
                        #if m in mnemonics_root:
                            #continue
                        #else:
                            #mnemonics_root.append (m)
                            #break
                    
                    #menu_label = menu_label.replace (m, '_' + m, 1)
                    shellitem = Gtk.MenuItem.new_with_mnemonic (menu_label)
                    shellitem.set_submenu (shell)
                    menuitems [v[0]] = shell
                    shell.append (item)
                    self.menu.append (shellitem)
                else:
                    menuitems [v[0]].append (item)
            else:
                menu_label = command.title ()
                menu_label = self.menu_item_set_mnemonic (menu_label)
                #m = menu_label [0]
                #for m in menu_label:
                    #if m in mnemonics_root:
                        #continue
                    #else:
                        #mnemonics_root.append (m)
                        #break
                
                #menu_label = menu_label.replace (m, '_' + m, 1)
                shellitem = Gtk.MenuItem.new_with_mnemonic (menu_label)
                #item = Gtk.MenuItem.new_with_mnemonic (command [:1].upper () + "_" + command [1:])
                item = Gtk.MenuItem.new_with_mnemonic (menu_label)
                self.menu.append (item)
            
            item.connect ("activate",self.hasher.commands [command])
            item.ui = self
            item.help = self.help

        self.entry_completion_store.set_value (self.entry_completion_store.append (), 0, " ")
        self.menu.append (Gtk.SeparatorMenuItem ())
        self.menu.append (Gtk.MenuItem.new_with_label ("Cancel"))
        self.menu.show_all ()
        self.menu_button.set_popup (self.menu)

        self.zoom_width = 0
        self.zoom_height = 0

        self.zoom_toolbar = Gtk.Toolbar ()
        self.zoom_toolbar.set_orientation (1)
        self.zoom_toolbar.set_style (0)
        zin = Gtk.ToolButton.new_from_stock ("gtk-zoom-in")
        zout = Gtk.ToolButton.new_from_stock ("gtk-zoom-out")
        z100 = Gtk.ToolButton.new_from_stock ("gtk-zoom-100")
        zfit = Gtk.ToolButton.new_from_stock ("gtk-zoom-fit")

        zin.connect ("clicked", self.zoom_in)
        zout.connect ("clicked", self.zoom_out)
        zfit.connect ("clicked", self.zoom_fit)
        z100.connect ("clicked", self.zoom_100)

        self.zoom_toolbar.insert (zin, -1)
        self.zoom_toolbar.insert (zout, -1)
        self.zoom_toolbar.insert (zfit, -1)
        self.zoom_toolbar.insert (z100, -1)

        self.zoom_toolbar_box = Gtk.VBox ()
        self.revealer = Gtk.Revealer ()
        self.zoom_toolbar_box.pack_start (self.revealer, 0, 0, 0)

        self.revealer.add (self.zoom_toolbar)
        self.zoom_toolbar_box.props.halign = Gtk.Align.END
        self.overlay.add_overlay (self.zoom_toolbar_box)

        self.infobar.timer = Timer ()
        #self.infobar.connect ('show', self.info_hide)
        infobar_font = Pango.FontDescription.from_string ("Ubuntu Mono 45")
        self.infobar.modify_font (infobar_font)

        self.image_sw.ui = self
        self.image_sw.connect ("enter-notify-event", lambda self, *w: self.ui.revealer.set_reveal_child (True) if self.ui.is_video_playing () else self.ui.revealer.set_reveal_child (False))
        self.connect ("leave-notify-event", lambda self, *w: self.revealer.set_reveal_child (False))
    
        #self.image_event_box.connect ("button-press-event", lambda self, *w: print (w[0].x))
        self.image_event_box.connect ("button-press-event", self.set_focus)

        self.camera_signature = 0

        self.menu_button.set_tooltip_text ("Menu")

        self.message ("Welcome", "ui")
        self.message ("This is Cicada version {}".format (get_version ()))

        self.entry.grab_focus ()

    def entry_completion_append (self, command):
        self.entry_completion_store.set_value (self.entry_completion_store.append (), 0, "#" + command)

    def gallery_do_search_like_fo_real (self, text):
        iter = self.gallery.store.get_iter_first ()
        while iter is not None:
            name = self.gallery.store.get (iter, 1) [0]
            if name is None or text is None:
                return
            if text in name:
                #print (name)
                path = self.gallery.store.get_path (iter)
                if path is not None:
                    self.gallery.unselect_all ()
                    self.gallery.select_path (path)
                    self.gallery.scroll_to_path (path, False, 0, 0)
                return
            #print (name)
            iter = self.gallery.store.iter_next (iter)

    def filter_host_filter (self, image):
        for a in self.filter_host.filters:
            if self.filter_host.filters [a].enabled.get_active ():
                try:
                    image = self.filter_host.filters [a].filter (image)
                except cv2.error as e:
                    self.message (str (e), "error")
                    self.filter_host.filters [a].enabled.set_active (False)
                    #self.notebook.set_current_page (0)
        return image

    def gallery_do_search (self, event):
        self.gallery.search.entry.handle_event (event)
        #search.connect ('closed', lambda *w: print ('s'))
        #search.set_size_request (200,100)
        self.gallery.search.show_all ()
        self.gallery.search.popup ()
        self.gallery.search.entry.do_move_cursor (self.gallery.search.entry, 1, 1,0)
        
    def gallery_search (self, widget, event):
        if len (Gdk.keyval_name (event.keyval)) == 1 and Gdk.keyval_name (event.keyval).isalpha ():
            #print (Gdk.keyval_name (event.keyval))
            if event.state == 0:
                self.gallery.search.entry.set_text ('')
            self.gallery_do_search (event)
            return True
        else:
            return False

    def menu_item_set_mnemonic (self, menu_label):
        menu_label = menu_label.replace (menu_label [0], '_' + menu_label [0], 1)
        return menu_label
    
    def sleep_interval_set (self, *w):
        self.sleep_interval = self.sleep_spin.get_value ()        

    def get_default_zoom (self):
        minimum, natural = self.image_sw.get_preferred_size ()
        return natural.width, natural.height

    def gallery_item_activated (self, iconview, path):
        if path == None:
            path = self.gallery.get_selected_items () [0]
        if path == None:
            return
        it = self.gallery.store.get_iter (path)
        name = self.gallery.store.get (it, 2) [0]
        self.picture_load (fname = name)

    def gallery_open (self, path = None):
        # if path is None:
        if not isinstance (path, str):
            path = self.prompt_filename (title = "Select folder", action = Gtk.FileChooserAction.SELECT_FOLDER)
            if path is None:
                return

        if not path [-1] == '/':
            path += '/'
        
        # find a better way to do this!
        jpg = glob.glob (path + '*jpg')
        png = glob.glob (path + '*png')
        gif = glob.glob (path + '*gif')
        bmp = glob.glob (path + '*bmp')
        files = jpg + png + gif + bmp
        
        if not (len (files)):
            return
        
        self.gallery.store.clear ()
        
        for f in files:
            pixbuf = None
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale (f, 256, 256, True)
            except Exception as e:
                print (f, e)
                self.message (f + ': ' + str (e), 'ui-error')
            
            if pixbuf:
                self.gallery.store.append ([pixbuf, os.path.basename (f), f])
        self.message ("loaded folder {}".format (path), 'ui')
    
    def peep_contour (self, cn = None):
        if cn is None:
            cn, scale = self.prompt_vars ([str, int], 'Enter contour and scale')
            if cn is None:
                return
            if scale == 0:
                scale = 5

        image = generate_image_from_contour (dispersion_to_contour (str (cn), scale = scale))
        self.peep (image)
    
    def get_focus_coords (self, mode):
        if isinstance (mode, int):
            mode = FocusMode (mode)
        elif isinstance (mode, str):
            mode = FocusMode [mode]

        if mode == FocusMode.color:
            return self.colorfocus.center, (self.colorfocus.sidex, self.colorfocus.sidey)
        elif mode == FocusMode.contour or mode == FocusMode.contour_clusters:
            return self.contourfocus.center

    def drag (self, dxy):
        window, x, y, mod = self.image.get_window ().get_pointer ()
        
        sidex = int ((x - dxy [0]) / 2)
        sidey = int ((y - dxy [1]) / 2)
        if sidex > 0 and sidey > 0:
            self.colorfocus.sidex = sidex
            self.colorfocus.sidey = sidey
        self.colorfocus.center = [dxy [0] + int ((x - dxy [0]) / 2), dxy [1] + int ((y - dxy [1]) / 2)]
        self.contourfocus.center = [dxy [0] + int ((x - dxy [0]) / 2), dxy [1] + int ((y - dxy [1]) / 2)]
        #self.colorfocus.center = [dxy [0], dxy [1]]
        return self.dragging

    def print_selection (self, *w):
        cn = self.contourfocus.get (self.current_frame, raw = True, current = False)
        if cn is None:
            return None
        
        for i in self.contourfocus.selection:
            self.message (str ('[{}] '.format (i)) + str (cn [i]) + '\nlen: ' + str (len (cn [i])), 'ui')

    def set_selection (self, *w):
        if self.focus_mode is FocusMode.contour or self.focus_mode is FocusMode.contour_multi:
            cn = self.contourfocus.get (self.current_frame, raw = True, current = False)
        elif self.focus_mode is FocusMode.contour_es or self.focus_mode is FocusMode.contour_es_multi:
            cn = self.contourfocus.get (self.current_frame, raw = True, current = False, es = True)
        else:
            return None

        if cn is None:
            return None

        self.contour.selection.set_range (0, len (cn))
        selection = self.contour.selection.get_value_as_int ()
        
        if selection >= len (cn):
            return
        
        cn = cn [selection][0][0][0], cn [selection][0][0][1]
        self.contourfocus.center = [cn [0], cn [1]]
        self.contourfocus.selection = [selection]
    
    def blur_frame (self, image):
        try:
            current = self.blur.simple
            if self.blur.simple.get_active ():
                image = cv2.blur (image, (self.blur.simple.ksize.get_value_as_int (),self.blur.simple.ksize.get_value_as_int ()))
            
            current = self.blur.box
            if self.blur.box.get_active ():
                image = cv2.boxFilter (image, -1, (self.blur.box.ksize.get_value_as_int (), self.blur.box.ksize.get_value_as_int ()), None, None, self.blur.box.normalize.get_active ())
            
            current = self.blur.median
            if self.blur.median.get_active ():
                image = cv2.medianBlur (image, self.blur.median.ksize.get_value_as_int ())
            
            current = self.blur.gaussian
            if self.blur.gaussian.get_active ():
                image = cv2.GaussianBlur (image, (self.blur.gaussian.ksize.get_value_as_int (), self.blur.gaussian.ksize.get_value_as_int ()), self.blur.gaussian.sigmax.get_value_as_int (), None, self.blur.gaussian.sigmay.get_value_as_int ())
            
            current = self.blur.dilate
            if self.blur.dilate.get_active ():
                if self.blur.dilate.erode.get_active ():
                    image = cv2.erode (image, cv2.getStructuringElement (self.blur.dilate.shape.get_value_as_int (), (self.blur.dilate.ksize.get_value_as_int (), self.blur.dilate.ksize.get_value_as_int ())), None, (-1, -1), self.blur.dilate.iterations.get_value_as_int ())
                else:
                    image = cv2.dilate (image, cv2.getStructuringElement (self.blur.dilate.shape.get_value_as_int (), (self.blur.dilate.ksize.get_value_as_int (), self.blur.dilate.ksize.get_value_as_int ())), None, (-1, -1), self.blur.dilate.iterations.get_value_as_int ())

            current = self.blur.bil
            if self.blur.bil.get_active ():
                image = cv2.bilateralFilter (image, self.blur.bil.d.get_value_as_int (), self.blur.bil.sigma_color.get_value_as_int (), self.blur.bil.sigma_space.get_value_as_int ())

        except Exception as e:
            # Yo dis da shit right here
            current.set_active (False)
            self.message ('Error applying blur!\n{}'.format (str(e)), 'ui-error')
        return image
    
    def filter_frame (self, image):
        if self.filters.scale.get_active ():
            width = self.filters.scale.width.get_value_as_int ()
            height = self.filters.scale.height.get_value_as_int ()
            
            image = cv2.resize (image, (width, height))
        
        if self.filters.rotate.get_active ():
            height, width,  something = image.shape
            angle = self.filters.rotate.angle.get_value_as_int ()
            matrix = cv2.getRotationMatrix2D ((width / 2, height / 2), angle ,1)
            image = cv2.warpAffine (image, matrix, (width, height))
        
        if self.filters.zoom.get_active ():
            height, width,  something = image.shape
            value = self.filters.zoom.value.get_value_as_int ()
            (center_x, center_y), (side_x, side_y) = self.get_focus_coords (FocusMode.color)
            source = [[center_x - side_x, center_y - side_y],
                    [center_x + side_x, center_y - side_y],
                    [center_x - side_x, center_y + side_y],
                    [center_x + side_x, center_y + side_y]]
            x1 = value if self.filters.zoom.x1.get_active () else -value
            y1 = value if self.filters.zoom.y1.get_active () else -value
            x2 = value if self.filters.zoom.x2.get_active () else -value
            y2 = value if self.filters.zoom.y2.get_active () else -value
            x3 = value if self.filters.zoom.x3.get_active () else -value
            y3 = value if self.filters.zoom.y3.get_active () else -value
            x4 = value if self.filters.zoom.x4.get_active () else -value
            y4 = value if self.filters.zoom.y4.get_active () else -value
            
            dest = [[center_x - side_x + x1, center_y - side_y + y1],
                    [center_x + side_x + x2, center_y - side_y + y2],
                    [center_x - side_x + x3, center_y + side_y + y3],
                    [center_x + side_x + x4, center_y + side_y + y4]]
            matrix = cv2.getPerspectiveTransform (np.float32 (source), np.float32 (dest))
            image = cv2.warpPerspective (image, matrix, (width, height))

        return image
            
    
    def save_current_frame (self):
        self.save_image (self.get_frame ())
    
    def save_image (self, frame):
        filename = self.prompt_filename (title = 'Save file', action = 1)
        if filename is None:
            return
        
        if not '.jpg' in filename:
            filename += '.jpg'

        if os.path.exists (filename):
            if not self.prompt_vars ([bool], 'Overwrite file?\n{}'.format (filename)) [0]:
                return
        
        cv2.imwrite (filename, frame)
        self.info ('Saved current frame to {}'.format (filename))
        self.message ('Saved current frame to {}'.format (filename))
    
    def set_selection_all (self):
        if self.focus_mode is FocusMode.contour or self.focus_mode is FocusMode.contour_multi:
            cn = self.contourfocus.get (self.current_frame, raw = True, current = False)
        elif self.focus_mode is FocusMode.contour_es or self.focus_mode is FocusMode.contour_es_multi:
            cn = self.contourfocus.get (self.current_frame, raw = True, current = False, es = True)
        else:
            return None
        
        if cn is None:
            return None
            
        self.contourfocus.select_all (cn)
        self.contourfocus.center = [cn [0][0][0][0], cn [0][0][0][1]]
        return None
        
    def set_selection_range_hook (self):
        selection = self.prompt_vars ([int, int], 'enter range')
        self.set_selection_range (selection)
        
    def set_selection_range_from_spin (self):
        select_from = self.contour.select_from.get_value_as_int ()
        select_to = self.contour.select_to.get_value_as_int ()
        
        if select_from == -1 or select_to == -1 or select_from >= select_to:
            if select_from > select_to:
                self.contour.select_from.set_value (select_to)
                self.contour.select_to.set_value (select_from)
            return
        
        #if select_to == 0:
            #select_to += 1
        #elif select_to > 1:
        #select_to -= 1
        self.set_selection_range ([select_from, select_to])

    def set_selection_range (self, selection):
        if self.focus_mode is FocusMode.contour or self.focus_mode is FocusMode.contour_multi:
            cn = self.contourfocus.get (self.current_frame, raw = True, current = False)
        elif self.focus_mode is FocusMode.contour_es or self.focus_mode is FocusMode.contour_es_multi:
            cn = self.contourfocus.get (self.current_frame, raw = True, current = False, es = True)
        else:
            return None
        
        if cn is None:
            return None

        self.contourfocus.select_range (cn, selection [0], selection [1])
        self.contourfocus.center = [cn [selection [0]][0][0][0], cn [selection [0]][0][0][1]]
        return None
        

    def set_focus (self, widget, event, *w):
        #print (int (event.state))
        #if int (event.state) == 21 or int (event.state) == 5:
        if int (event.state) == Gdk.ModifierType.SHIFT_MASK:
            cn = None
            if self.focus_mode is FocusMode.contour or self.focus_mode is FocusMode.contour_multi:
                cn = self.contourfocus.get (self.current_frame, raw = True, current = False)
            elif self.focus_mode is FocusMode.contour_es or self.focus_mode is FocusMode.contour_es_multi:
                cn = self.contourfocus.get (self.current_frame, raw = True, current = False, es = True)
            else:
                return None
            if cn is None:
                return None
            
            self.contourfocus.append_contour_to_selection_at_coords (cn, (event.x, event.y))
            return
        
        if self.dragging:
            self.dragging = False
            return
            
        #if event.type == Gdk.EventType._2BUTTON_PRESS or int (event.state) == 4 or int (event.state) == 20:
        if event.type == Gdk.EventType._2BUTTON_PRESS or int (event.state) == Gdk.ModifierType.CONTROL_MASK:
            self.dragging = True
            self.colorfocus.sidex = 1
            self.colorfocus.sidey = 1
            window, x, y, mod = self.image.get_window ().get_pointer ()
            GLib.timeout_add (1, self.drag, (x,y))
            return
        
        if not self.focus_on:
            self.focus_toggle (True)

        if not int (event.state) == 1 and not int (event.state) == 17:
            self.colorfocus.center = [int (event.x), int (event.y)]
        self.contourfocus.center = [int (event.x), int (event.y)]

    def info_hide (self, *args):
        if round (self.infobar.timer.time (), 2) > 10.0:
            #print (round (self.infobar.timer.time (), 2))
            self.infobar_revealer.set_reveal_child (False)
            return False
        else:
            return True

    def info (self, * args, image = None):
        #print (image, debug_info ())
        text = str ()
        for a in args:
            if isinstance (a, str):
                text += a + ' '
        if '\n' in text:
            text = text.replace ('\n', ' ')
        
        if not self.infobar_revealer.get_reveal_child ():
            self.infobar_revealer.set_reveal_child (True)
            GLib.timeout_add (10, self.info_hide)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if image is not None:
                pixbuf = cv2_image_to_gdk_pixbuf (image)
                pixbuf = gdk_pixbuf_scale (pixbuf, self.PREVIEW_ICON_SIZE * 2, self.PREVIEW_ICON_SIZE) # because shape preview
                self.infobar.image.set_from_pixbuf (pixbuf)
            else:
                pixbuf = self.icon_theme.load_icon (self.PREVIEW_DEFAULT_ICON, self.PREVIEW_ICON_SIZE, Gtk.IconLookupFlags.FORCE_SIZE)
                self.infobar.image.set_from_pixbuf (pixbuf)
        
        self.infobar.label.set_text (text)
        self.infobar.timer.reset ()
        #self.info_hide ()

    def print_input (self, *args):
        self.message (str (args [1:]), 'ui')

    def append_text (self, text, attribute = "default"):
        #if attribute == 'info':
            #self.info (text)
            #return
    
        #if attribute is not "default":
            #text = "[{}] {}".format (attribute, text)
        # aye!
        # we get anything we can
        # and print the fuck out of it!
        if not isinstance (text, str):
            # we could convert to str individually
            # and drop everything that isn't a str,
            # but we _want_ to print everything
            # we can
            text = str (text)

        text = "<{}> {}".format (debug_info (), text)
        if 'error' in attribute:
            self.sounds.play ('error')
        
        self.text_buffer.insert_at_cursor (text, -1)
        start = self.text_buffer.get_iter_at_line (self.text_buffer.get_line_count () - (text.count ('\n') + 1))
        end = self.text_buffer.get_end_iter ()
        
        self.text_buffer.apply_tag_by_name (attribute, start, end)
        self.text_buffer.insert_at_cursor ("\n", -1)
        self.text_view_scroll_to_bottom ()
        
    def text_view_scroll_to_bottom (self):
        self.update_ui ()
        self.text_view_sw.get_vadjustment ().set_value (self.text_view_sw.get_vadjustment ().get_upper ())
        self.update_ui ()

    def update_ui (self):
        while self.maincontext.pending ():
            self.maincontext.iteration ()

    def prompt_filename (self, title = "Open file", action = Gtk.FileChooserAction.OPEN):
        dialog = Gtk.FileChooserDialog (title = title,
                    action = action,
                    buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        
        
        
        dialog.set_default_response (Gtk.ResponseType.CANCEL)
        if dialog.run () == Gtk.ResponseType.CANCEL:
            dialog.destroy ()
            return
        
        filename = dialog.get_filename ()
        dialog.destroy ()

        return filename

    def start_video (self, *args):
        filename = None

        if len (args) > 1:
            filename = args [1][0]
            self.start_camera (filename = filename)
            return
        
        filename = self.prompt_filename ()
        
        if filename:
            self.start_camera (filename = filename)
    
    def pause_camera (self, *args):
        self.camera_paused = True

    def unpause_camera (self, *args):
        self.camera_paused = False
    
    def seek_video (self, *args):
        if len (args) > 1:
            frames = int (args [1][0])
        else:
            frames = 200
        
        self.camera.seek (frames)
        self.message ("Seeking {} frames".format (frames), "ui")

    def get_frame (self, raw = False, focused = False, pixbuf = False):
        if raw:
            return self.camera.get_frame (raw = True)
        elif focused:
            if not pixbuf:
                return self.focused_frame
            else:
                return self.focused_pixbuf
        else:
            return self.current_frame
    
    def bridge_current_id (self):
        self.message (self.manager.ui_instances.index (self))
    
    def bridge_list_ui (self):
        self.message (self.manager.ui_instances)
        
    def camera_get_focus (self, focus_mode = None, raw = False, multi = False, clusters = False, current = True):
        # why so many ifs and butts?
        # this should be a simple
        # return self.focus_mode.get (args)
        
        if isinstance (focus_mode, int):
            focus_mode = FocusMode (focus_mode)
        elif isinstance (focus_mode, str):
            focus_mode = FocusMode [focus_mode]
        elif focus_mode is not None and not isinstance (focus_mode, FocusMode):
            raise NotImplementedError (focus_mode)

        #if isinstance (focus_mode, str):
            #if hasattr (FocusMode, focus_mode):
                #focus_mode = FocusMode [focus_mode]

        if focus_mode is None:
            focus_mode = self.focus_mode
        
        #if raw and focus_mode != FocusMode.contour:
            #raise NotImplementedError
        
        if focus_mode == FocusMode.color:
            return self.colorfocus.get (self.current_frame)
        elif focus_mode == FocusMode.contour:
            return self.contourfocus.get (self.current_frame, raw = raw, current = current, multi = multi)
        elif focus_mode == FocusMode.contour_es:
            return self.contourfocus.get (self.current_frame, raw = raw, current = current, es = True, multi = multi)
        elif focus_mode == FocusMode.contour_multi:
            return self.contourfocus.get (self.current_frame, raw = raw, multi = True, current = current)
        elif focus_mode == FocusMode.contour_es_multi:
            return self.contourfocus.get (self.current_frame, raw = raw, es = True, multi = True, current = current)
        elif focus_mode == FocusMode.raw:
            return self.current_frame
        elif focus_mode == FocusMode.contour_clusters:
            if clusters:
                return self.contourfocus.generate_contour_clusters ()
            else:
                return self.contourfocus.get (self.current_frame, raw = raw, multi = multi, current = current)
        elif focus_mode == FocusMode.orb:
            return self.orbfocus.get (self.current_frame, raw = raw)
        elif focus_mode == FocusMode.orb_es:
            return self.orbfocus.get (self.current_frame, raw = raw, es = True)
        elif focus_mode == FocusMode.fast:
            return self.fastfocus.get (self.current_frame, raw = raw)
        elif focus_mode == FocusMode.fast_es:
            return self.fastfocus.get (self.current_frame, raw = raw, es = True)
        else:
            raise NotImplementedError ('unsupported focus mode ' + str (focus_mode))
        
    def peep (self, image):
        p = Gtk.Popover.new (self.entry)
        image = Gtk.Image.new_from_pixbuf (cv2_image_to_gdk_pixbuf (image))
        p.add (image)
        p.show_all ()
        
    def prompt_vars (self, var_list, message = None):
        vbox = Gtk.VBox ()
        if message:
            label = Gtk.Label (message)
            label.set_line_wrap (True)
            label.set_ellipsize (2)
            vbox.pack_start (label, 0, 0, 0)
        
        box = Gtk.HBox ()
        vbox.pack_start (box, 1, 1, 0)

        dialog = Gtk.Dialog (parent = self)
        
        widgets = []
        for v in var_list:
            b = None
            if v is int:
                b = Gtk.SpinButton.new_with_range (0, 10000, 1)
                b.connect ('activate', lambda self, *w: dialog.response (0))
                widgets.append (b.get_value_as_int)
            elif v is str:
                b = Gtk.Entry ()
                b.connect ('activate', lambda self, *w: dialog.response (0))
                widgets.append (b.get_text)
            elif v is bool:
                b = Gtk.CheckButton ()
                #b.connect ('activate', lambda self, *w: dialog.response (0))
                widgets.append (b.get_active)
            elif v is Gdk.Color:
                c = Gdk.Color (red = 65535, green = 65535, blue = 65535)
                #c.parse ('#ffffff')
                b = Gtk.ColorButton.new_with_color (c)
                widgets.append (b.get_color)
                        
            if b:
                box.pack_start (b, 0, 0, 0)

        #p = Gtk.Popover.new (self.entry)
        #p.set_modal (True)
        #p.add (vbox)
        #p.show_all ()
        
        dialog.get_content_area ().add (vbox)
        dialog.add_button ('Okay!', 0)
        vbox.show_all ()
        dialog.run ()
        
        ret = []
        for i in widgets:
            ret.append (i ())
        
        dialog.destroy ()
        return ret

    def camera_show_focus (self):
        f = self.camera_get_focus ()
        if f is None:
            warnings.warn ('focus returned None')
            self.message ('focus returned None', 'ui-error')
            return None
        
        p = Gtk.Popover.new (self.entry)
        box = Gtk.VBox ()
        image = Gtk.Image.new_from_pixbuf (cv2_image_to_gdk_pixbuf (f))
        box.pack_start (image, 1, 1, 0)
        save = Gtk.Button.new_with_label ('Save to file')
        box.pack_start (save, 0, 0, 0)
        save.connect ('clicked', lambda *w: self.save_image (f))
        p.add (box)
        p.show_all ()
        #self.update_ui ()
    
    def start_camera (self, *args, filename = 0):
        if filename is not 0:
            self.message ("Loading video {}".format (filename), "ui")
        if not self.camera.open (device = filename):
            self.message ("video input unavailable!", "ui-error")
            return
        
        self.play ()
    
    def play (self, camera = None):
        self.sounds.play ('default')
        #GLib.timeout_add (self.sleep_interval, self.play_do, camera)
        self.curiosity.main ()
        

    def poll_image (self):
        cv2_image = self.camera.get_frame ()
        if cv2_image is None:
            return None
        # filters
        cv2_image = self.filter_frame (cv2_image)
        #blur
        cv2_image = self.blur_frame (cv2_image)
        # filters! heh
        cv2_image = self.filter_host_filter (cv2_image)

        self.current_frame = copy.copy (cv2_image)
        
        if self.focus_on:
            return self.colorfocus.draw (cv2_image)
        else:
            return cv2_image
        
    def play_do (self, camera = None):
        #print ('play ()')
        if not self.play_button.get_active ():
            return
        
        if camera == None:
            camera = self.camera
        
        self.camera_signature = time ()
        self.camera_paused = False
        signature = self.camera_signature
        
        image = camera.get_pixbuf ()
        if image is None:
            #self.image.set_from_pixbuf (self.icon_theme.load_icon ('error', 256, Gtk.IconLookupFlags.GENERIC_FALLBACK))
            self.logofy (error = True)
            self.message ('camera.get_pixbuf () returned None!', 'error')
            self.update_ui ()
            return False
        #if self.zoom_width is 0 or self.zoom_height is 0:
        
        #todo: i don't get it. I am resetting the zoom values here myself
        # why?
        #self.zoom_width, self.zoom_height = self.get_default_zoom ()
        #self.zoom_width, self.zoom_height = resize_calculator (image.get_width (), image.get_height (), self.zoom_width, self.zoom_height)
        
        if (signature == self.camera_signature):
            if not self.camera_paused:
                cv2_image = camera.get_frame ()
                # filters
                cv2_image = self.filter_frame (cv2_image)
                #blur
                cv2_image = self.blur_frame (cv2_image)
                # filters! heh
                cv2_image = self.filter_host_filter (cv2_image)

                self.current_frame = copy.copy (cv2_image)
                
                # To do: replace this with a switch/case dict ()
                if self.focus_on:
                    if self.focus_mode == FocusMode.color:
                        focused_image = self.colorfocus.draw (cv2_image)
                    elif self.focus_mode == FocusMode.contour or self.focus_mode == FocusMode.contour_multi or self.focus_mode == FocusMode.contour_clusters:
                        focused_image = self.contourfocus.draw (cv2_image)
                    elif self.focus_mode == FocusMode.contour_es or self.focus_mode == FocusMode.contour_es_multi:
                        focused_image = self.contourfocus.draw (cv2_image, es = True)
                    elif self.focus_mode == FocusMode.fast:
                        focused_image = self.fastfocus.draw (cv2_image)
                    elif self.focus_mode == FocusMode.fast_es:
                        focused_image = self.fastfocus.draw (cv2_image, es = True)
                    elif self.focus_mode == FocusMode.orb:
                        focused_image = self.orbfocus.draw (cv2_image)
                    elif self.focus_mode == FocusMode.orb_es:
                        focused_image = self.orbfocus.draw (cv2_image, es = True)
                    else:
                        raise NotImplementedError (self.focus_mode)
                else:
                    focused_image = cv2_image

                #self.current_frame = cv2_image
                self.focused_frame = copy.copy (focused_image)
                image = cv2_image_to_gdk_pixbuf (focused_image)
                if image is None:
                    self.message ('focus.draw () returned None!', 'ui-error')
                    self.focus_mode = FocusMode.color
                    return True
                
                self.focused_pixbuf = image
                
                #print (self.zoom_width, self.zoom_height)
                if self.zoom_width is 0 or self.zoom_height is 0:
                    self.zoom_width, self.zoom_height = self.get_default_zoom ()
                    self.zoom_width, self.zoom_height = resize_calculator (image.get_width (), image.get_height (), self.zoom_width, self.zoom_height)
                elif self.zoom_width is -1 or self.zoom_height is -1:
                    self.zoom_width = image.get_width ()
                    self.zoom_height = image.get_height ()
                    
                image = image.scale_simple (self.zoom_width, self.zoom_height, GdkPixbuf.InterpType.BILINEAR)
                self.image.set_from_pixbuf (image)
            
            self.update_ui ()
            #sleep (self.sleep_interval)
            
            #if not self.mainloop.is_running ():
            #if not self.manager.mainloop.is_running ():
                #break
        #print ('exit play ()')
        if not self.manager.mainloop.is_running () or not self.is_visible () or self.camera_paused:
            camera.close ()
            return False
        return True
    
    def stop_camera (self, *args):
        self.camera_signature = 0 #time ()
        self.logofy ()
    
    def is_video_playing (self):
        return self.camera_signature

    open_modes = {
        Mode.none: lambda self, uri: None,
        Mode.camera: lambda self, uri: self.start_camera (),
        Mode.picture: lambda self, uri: self.picture_load (fname = uri),
        Mode.video: lambda self, uri: self.start_camera (filename = uri),
        Mode.folder: lambda self, uri: self.gallery_open (uri),
        Mode.canvas: lambda self, uri: self.canvas_new_image (uri)
    }

class UIManager:
    ui_instances = None #[]
    idle = None # []
    #plugin_host = None
    pool = None #multiprocessing.Pool ()
    
    def submit_job (self, func, data):
        # check to see if data is list_ish
        assert hasattr (data, "__len__")
        return self.pool.map (func, data)
        
            
    def ui_remove (self, ui):
        self.ui_instances.remove (ui)
        if not len (self.ui_instances):
            self.main_quit ()
    
    def idle_add (self, func):
        self.idle.append (func)
    
    def idle_do (self, index = None):
        if index is not None:
            #self.idle [index] ()
            GLib.idle_add (self.idle [index])
            del (self.idle [index])
            return
        
        for i in range (len (self.idle)):
            self.idle [i] ()
            # this causes us to change the list
            # while the list is being iterated
            # don't do this
            #del (self.idle [i])
        
        self.idle = []
    
    def main (self):
        try:
            self.mainloop.run ()
        except KeyboardInterrupt as e:
            print (e)
            self.main_quit ()

    def main_quit (self, exit = False):
        self.mainloop.quit ()
        sys.exit () if exit else None

    def __init__ (self):
        self.ui_instances = list () # yeah!
        self.idle = list ()
        self.mainloop = GLib.MainLoop ()
        self.mainloop.context = self.mainloop.get_context ()
        #self.plugin_host = PluginHost (self)
        self.pool = Pool ()
        
    def ui_add (self, mode = None, uri = None):
        ui = UI (self, mode, uri)
        #for i in self.plugin_host.get_plugins ():
            #ui.hasher.append ('plugin-' + p, lambda *w: print (p))
            #ui.entry_completion_append ('plugin-' + p)
        ui.hasher.append ('manager-new-window', lambda *w: self.new_ui ())
        ui.entry_completion_append ('manager-new-window')
        ui.hasher.append ('manager-quit', lambda *w: self.main_quit (True))
        ui.entry_completion_append ('manager-quit')
        self.ui_instances.append (ui)
        return ui

    def new_ui (self):
        w = self.ui_add ()
        self.init (w)
    
    def init (self, w):
        w.show_all ()
        w.update_ui ()
        if Gdk.Keymap.get_default ().get_num_lock_state ():
            w.message ("Num lock is on! Might cause problems with modifier keys", 'ui-error')
        

    def startup (self, args = None):
        if args:
            if args.camera:
                w = self.ui_add (mode = UI.Mode.camera)
            if args.video:
                for v in args.video:
                    assert os.path.isfile (v), v
                    w = self.ui_add (mode = UI.Mode.video, uri = v)
            if args.picture:
                for p in args.picture:
                    assert os.path.isfile (p)
                    w = self.ui_add (mode = UI.Mode.picture, uri = p)
            if args.folder:
                for f in args.folder:
                    assert os.path.isdir (f), '{} is not a directory!'.format (f)
                    w = self.ui_add (mode = UI.Mode.folder, uri = f)
            if args.canvas:
                w = self.ui_add (mode = UI.Mode.canvas, uri = args.canvas)
        # no arguments
        # be polite and open an empty window
        if not len (self.ui_instances):
            w = self.ui_add ()

        for w in self.ui_instances:
            self.init (w)
        self.idle_do ()
        self.main ()

def main(args):
    GLib.set_application_name ("cicada " + get_version ())
    #print ("cicada " + version + " waking up ...")
    parser = ArgumentParser ()
    parser.add_argument ("-c", "--camera", help = "Open camera", action = "store_true")
    parser.add_argument ("-v", "--video", help = "Open video", nargs = "+")
    parser.add_argument ("-f", "--folder", help = "Open folder", nargs = "+")
    parser.add_argument ("-p", "--picture", help = "Open picture", nargs = "+")
    parser.add_argument ("-a", "--canvas", help = "New canvas (wxh)")
    parser.add_argument ("-m", "--maximize", help = "Maximize", action="store_true")
    args = parser.parse_args ()
    
    #GLib.idle_add (lambda: GLib.idle_add (lambda: w.info ('Welcome')))
    #print ("cicada up and running")
    #GLib.idle_add (lambda: w.message ("Num lock is on! Might cause problems with modifier keys", 'ui-error') if Gdk.Keymap.get_default ().get_num_lock_state () else True)
    
    manager = UIManager ()
    #manager.pool = multiprocessing.Pool ()
    manager.startup (args)
    
    return 0

if __name__ == '__main__':
# aye, hack!
    #from multiprocessing import pool
    #class Pool(multiprocessing.pool.Pool):
        #class Process(multiprocessing.Process):
            ## make 'daemon' attribute always return False
            #def _get_daemon(self):
                #return False
            #def _set_daemon(self, value):
                #pass
                
            #daemon = property(_get_daemon, _set_daemon)
    
    import sys
    sys.exit(main(sys.argv))

class GenericWindow (Gtk.Window):
    icon_theme = Gtk.IconTheme.get_default ()

    def __init__ (self):
        Gtk.Window.__init__ (self)
        self.connect ("destroy", lambda *w: self.main_quit ())
        self.connect ("key-press-event", self.hotkeys)
        self.mainloop = GLib.MainLoop ()
        self.mainloop.context = self.mainloop.get_context ()
        
    shortcuts = {
        Gdk.KEY_Escape: lambda self: self.main_quit (exit = True),
        Gdk.KEY_Return: lambda self: self.main_quit ()
    }

    def hotkeys (self, window, event):
        if event.keyval in self.shortcuts:
            self.shortcuts [event.keyval] (self)
            return True

    def update (self):
        while self.mainloop.context.pending ():
            self.mainloop.context.iteration ()

    def main (self):
        self.show_all ()
        try:
            self.mainloop.run ()
        except KeyboardInterrupt as e:
            print (e)
            self.main_quit ()

    def main_quit (self, exit = False):
        self.mainloop.quit ()
        sys.exit () if exit else None

class GenericImageViewer (GenericWindow):
    def __init__ (self, filename = None):
        super ().__init__ ()
        self.image = Gtk.Image ()
        if isinstance (filename, str):
            if os.path.exists (filename):
                self.image.set_from_file (filename)
        elif isinstance (filename, np.ndarray):
            im = cv2_image_to_gdk_pixbuf (filename)
            self.image.set_from_pixbuf (im)
        else:
            self.image.set_from_pixbuf (self.icon_theme.load_icon ('info', 256, Gtk.IconLookupFlags.GENERIC_FALLBACK))
        self.add (self.image)

    def set (self, filename):
        if isinstance (filename, str):
            if os.path.exists (filename):
                self.image.set_from_file (filename)
        elif isinstance (filename, np.ndarray):
            im = cv2_image_to_gdk_pixbuf (filename)
            self.image.set_from_pixbuf (im)
        else:
            self.image.set_from_pixbuf (self.icon_theme.load_icon ('gtk-error', 256, Gtk.IconLookupFlags.GENERIC_FALLBACK))
        self.image.show ()
