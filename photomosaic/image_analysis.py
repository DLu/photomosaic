
from image_functions import *
import color_spaces as cs

def analyze_this(img):
    regions = split_quadrants(img)
    rgb = map(dominant_color, regions) 
    lab = map(cs.rgb2lab, rgb)
    return rgb, lab
