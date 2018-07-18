#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2016-06-30

import sys
from input.input import Input
import cv2
import numpy as np
from utils import Thread, Timer

def get_color (image, x, y):
    return image [y, x]

def get_mean_color_multi_thread (mythread, thread_number):
    args = mythread.args
    image = args ["image"]

    blue = red = green = counter = 0

    for y in range (int (thread_number * (image.shape [0] / mythread.threads)), (int ((thread_number + 1) * (image.shape [0] / mythread.threads)))):
        for x in range (image.shape [1]):
            blue += image [y, x][0]
            green += image [y, x][1]
            red += image [y, x][2]
            counter += 1

    blue = blue / counter
    green = green / counter
    red = red / counter
    
    mythread.queues [thread_number] .put ([int (blue), int (green), int (red)])


def get_mean_color_multi (image):
    args = dict ()
    args ["image"] = image
    number_of_threads = 4
    
    mythread = Thread (number_of_threads, get_mean_color_multi_thread, args)
    mythread.start ()
    mean = mythread.get_data ()
    mythread.join ()
    blue = red = green = 0
    
    for i in mean:
        blue += i [0]
        green += i [1]
        red += i [2]

    blue = int (blue / number_of_threads)
    green = int (green / number_of_threads)
    red = int (red / number_of_threads)
    
    return (blue,green,red)
    
def get_mean_color (image):
    blue = green = red = 0
    counter = 0
    
    for y in range (image.shape [0]):
        for x in range (image.shape [1]):
            blue += image [y, x][0]
            green += image [y, x][1]
            red += image [y, x][2]
            counter += 1

    blue = blue / counter
    green = green / counter
    red = red / counter
    
    return int (blue), int (green), int (red)

if __name__ == '__main__':
    t = Timer ()
    image = cv2.imread (sys.argv [1])
    print (get_mean_color_multi (image))
    print (t.time ())
    t.reset ()
    print (get_mean_color (image))
    print (t.time ())
    
