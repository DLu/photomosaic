
from memo import memo
from PIL import Image
import logging
import color_spaces as cs
from image_functions import *

# Configure logger.
FORMAT = "%(name)s.%(funcName)s:  %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

@memo
def open_tile(filename, temp_size=(100,100)):
    """This memoized function only opens each image once."""
    im = Image.open(filename)
    im.thumbnail(temp_size, Image.ANTIALIAS) # Resize to fit within temp_size without cropping.
    return im


class Tile(object):
    """Tile wraps the Image class, so all methods that apply to images (show,
    save, crop, size, ...) apply to Tiles. Tiles also store contextual
    information that is used to reassembled them in the end."""
    def __init__(self, img, x, y, mask=None, ancestry=[], ancestor_size=None):
        self._img = img
        self.x = x
        self.y = y
        self._mask = mask.convert("L") if mask else None
        self._blank = None # meaning undetermined (so far)
        self._ancestry = ancestry
        self._depth = len(self._ancestry)
        if ancestor_size:
            self._ancestor_size = ancestor_size
        else:
            self._ancestor_size = self.size

    def crop(self, *args):
        if self._mask: self._mask.crop(*args)
        return self._img.crop(*args)

    def resize(self, *args):
        if self._mask: self._mask.resize(*args)
        return self._img.resize(*args)

    def __getattr__(self, key):
        if key == '_img':
            raise AttributeError()
        return getattr(self._img, key)

    def pos(self):
        return self.x, self.y 

    def avg_color(self):
        t = [0]*3
        for rgb in self._rgb:
            for i, c in enumerate(rgb):
                t[i] += c
        return [a/len(self._rgb) for a in t] 

    @property
    def ancestry(self):
        return self._ancestry

    @property
    def depth(self):
        return self._depth

    @property
    def ancestor_size(self):
        return self._ancestor_size

    @property
    def rgb(self):
        return self._rgb

    @rgb.setter
    def rgb(self, value):
        self._rgb = value

    @property
    def lab(self):
        return self._lab

    @lab.setter
    def lab(self, value):
        self._lab = value

    @property
    def match(self):
        return self._match

    @match.setter
    def match(self, value):
        self._match = value # sqlite Row object
        try:
            self._match_img = open_tile(self._match['filename'],
                (2*self._ancestor_size[1], 2*self.ancestor_size[0]))
                # Reversed on purpose, for thumbnail. Largest possible size
                # we could want later.
        except IOError:
            logger.error("The filename specified in the database as "
                         "cannot be found. Check: %s", self._match['filename'])

    @property
    def match_img(self):
        return self._match_img

    @property
    def blank(self):
        return self._blank
        
    def analyze(self):
        """"Determine dominant colors of target tile, and save that information"""
        if self.blank:
            return
        regions = split_quadrants(self)
        self.rgb = map(dominant_color, regions) 
        self.lab = map(cs.rgb2lab, self.rgb)

    def get_position(self, size, scatter=False, margin=0):
        """Return the x, y position of the tile in the mosaic, according for
        possible margins and optional random nudges for a 'scattered' look.""" 
        # Sum position of original ancestor tile, relative position of this tile's
        # container, and any margins that this tile has.
        ancestor_pos = [self.x*self.ancestor_size[0], self.y*self.ancestor_size[1]]
        if self.depth == 0:
            rel_pos = [[0, 0]]
        else:
            x_size, y_size = self.ancestor_size
            rel_pos = [[x*x_size//2**(gen + 1), y*y_size//2**(gen + 1)] \
                               for gen, (x, y) in enumerate(self.ancestry)]
            
        if self.size == size:
            padding = [0, 0]
        else:
            padding = map(lambda (x, y): (x - y)//2, zip(*([size, self.size])))
        if scatter:
            padding = [random.randint(0, 1 + margin), random.randint(0, 1 + margin)]
        pos = tuple(map(sum, zip(*([ancestor_pos] + rel_pos + [padding]))))
        return pos

