from input.featuredetect import key_points_to_contour
from input.contour import generate_image_from_contour, copy_contour_frame
import cv2, numpy as np
from random import randrange

class Plugin:
    def run (self):
        ui = self.host.manager.ui_instances [0]
        image = ui.get_frame ()
        cn = ui.contourfocus.get (ui.current_frame, raw = True, current = False, multi = True, es = ui.focus_mode.value == 3 or ui.focus_mode.value == 5)
        
        if ui.contourfocus.clusters is None or len (ui.contourfocus.clusters) == 0:
            ui.contourfocus.generate_contour_clusters ()
        
        print (len (ui.contourfocus.clusters))
        assert ui.contourfocus.clusters is not None, "ui.generate_contour_clusters () failed!"
        for c in ui.contourfocus.clusters:
            b = randrange (255)
            g = randrange (255)
            r = randrange (255)

            contour = np.ndarray ((0,1,2), np.int32)
            for i in c:
                #cv2.polylines (image, cn [i], True, (b,g,r), 3)
                contour = np.append (contour, cn [i], 0)
                #cv2.drawContours (image, cn, i, (0, 0, 255), -1)
            
            #cv2.polylines (image, contour, False, (b,g,r), 3)
            cv2.drawContours (image, contour, -1, (0, 0, 255), -3)
        
        ui.peep (image)
