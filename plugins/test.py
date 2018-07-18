from input.featuredetect import key_points_to_contour
import input.contour

import cv2, numpy as np

class Plugin:
    def run (self):
        image = self.ui.current_frame
        cn = self.ui.contourfocus.get (image, raw = True, multi = True)
        #dispersion = input.contour.contour_to_dispersion_hash (cn [0])
        #dispersion = input.contour.dispersion_reduce (dispersion, length = len (dispersion) - 50)
        #c = input.contour.dispersion_to_contour (dispersion)
        #image.fill (0)
        #cv2.drawContours (image, c, -1, (255,255,255), 2)
        #self.ui.peep (image)
        d1 = input.contour.contour_to_dispersion_hash (cn [0])
        d2 = input.contour.contour_to_dispersion_hash (cn [1])
        d1, d2 = input.contour.contour_fix_orientation (d1, d2)
        
        self.ui.message (input.contour.match_contour_dispersion (d1, d2))
        
        c = input.contour.dispersion_to_contour (d2)
        image.fill (0)
        cv2.drawContours (image, c, -1, (255,255,255), 2)
        self.ui.peep (image)
