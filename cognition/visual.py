#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  cicada
#  Shaji Khan  [djshaji@gmail.com]
#  2017-08-24

from cognition.processor import CognitiveProcessor
from input.visualsensoryinput import VisualSensoryInput

class VisualCognitiveProcessor (CognitiveProcessor):
    known_data_types = [VisualSensoryInput]
    
