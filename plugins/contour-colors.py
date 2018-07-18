from input.featuredetect import key_points_to_contour
from input.contour import generate_image_from_contour, copy_contour_frame
import cv2, numpy as np
from random import randrange

class Plugin:
    def run (self):
        image = self.ui.get_frame ()
        cn = self.ui.contourfocus.get (image, raw = True, multi = True)
        
        image.fill (0)
        cv2.drawContours (image, cn, -1, (255,255,255), 3)
        
        self.ui.peep (image)
