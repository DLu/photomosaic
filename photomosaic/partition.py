from __future__ import division
from image_functions import *
from math import floor, ceil
from random import randrange

FORMAT = "%(name)s.%(funcName)s:  %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

def to_int_coords(area):
    x,y,w,h = area
    x0 = int(floor(x))
    y0 = int(floor(y))
    w0 = int(ceil(x+w)-x0)
    h0 = int(ceil(y+h)-y0)
    return x0,y0,w0,h0
    
def procreate(area):
    """Divide image into quadrants, and return them all in a list.""" 

    x,y,w,h = area
    w/=2
    h/=2
    children = []
    for i in [0, 1]:
        for j in [0, 1]:
            children.append((x+w*i, y+h*j, w, h))
    return children

class Partition:
    def __init__(self, img, mask=None):
        self.img = img
        self.mask = mask
        self.areas = []
        self.tiles = None
        self.img_cache = {}
        self.mask_cache = {}

    def simple_partition(self, dimensions=10):
        "Partition the target image into a list of Tile objects."
        if isinstance(dimensions, int):
            dimensions = dimensions, dimensions

        width = self.img.size[0] / dimensions[0] 
        height = self.img.size[1] / dimensions[1]

        for y in range(dimensions[1]):
            for x in range(dimensions[0]):
                self.areas.append( (x*width, y*height, width, height) )
                
    def brick_partition(self, dimensions=10):
        if isinstance(dimensions, int):
            dimensions = dimensions, dimensions

        width = self.img.size[0] / dimensions[0] 
        height = self.img.size[1] / dimensions[1]

        for y in range(dimensions[1]):
            if y%2==0:
                for x in range(dimensions[0]):
                    self.areas.append( (x*width, y*height, width, height) )
            else:
                for x in range(dimensions[0]-1):
                    self.areas.append( (x*width+width/2, y*height, width, height) )
                self.areas.append( (0, y*height, width/2, height) )    
                self.areas.append( (self.img.size[0]-width/2, y*height, width/2, height) )    

    def recursive_split(self, depth=0, hdr=80):
        for g in xrange(depth):
            old_tiles = self.areas
            self.areas = []
            for tile in old_tiles:
                im = self.get_tile_img(tile)
                if dynamic_range(im) > hdr or self.straddles_mask_edge(tile):
                    # Keep children; discard parent.
                    self.areas += procreate(tile)
                else:
                    # Keep tile -- no children.
                    self.areas.append(tile)
            logging.info("There are %d tiles in generation %d",
                         len(self.areas), g)

    def straddles_mask_edge(self, tile):
        """A tile straddles an edge if it contains PURE white (255) and some
        nonwhite. A tile that contains varying shades of gray does not
        straddle an edge."""
        if not self.mask:
            return False
        mtile = self.get_mask_img(tile)
        darkest_pixel, brightest_pixel = mtile.getextrema()
        if brightest_pixel != 255:
            return False
        if darkest_pixel == 255:
            return False
        return True

    def remove_blanks(self, max_size=0.2):
        """Decide which tiles are blank. 
           Where the mask is grey, small tiles are blanked probabilistically. 
           (Small is defined as having a width smaller than
              max_size * img_width)"""
        if not self.mask:
            return
        new_tiles = []
        for tile in self.areas:
            mtile = self.get_mask_img(tile)
            brightest_pixel = mtile.getextrema()[1]
            if brightest_pixel == 255:
                new_tiles.append( tile )
            elif brightest_pixel == 0:
                continue
            elif tile[2] >= max_size * self.img.size()[0]:
                continue
            elif rand_range(255) < brightest_pixel:
                new_tiles.append( tile )
            
        logger.info("%d/%d tiles are set to be blank",
                    len(self.areas)-len(new_tiles), len(self.areas))
        self.areas = new_tiles

    def get_tiles(self):
        if self.tiles:
            return self.tiles
        self.remove_blanks()
        self.tiles = map(to_int_coords, self.areas)

    def get_cached_img(self, tile, cache, img):
        if type(tile[0])==float:
            tile = to_int_coords(tile)

        if tile not in cache:
            (x,y,w,h) = tile
            cache[tile] = img.crop((x, y, x+w, y+h))

        return cache[tile]

    def get_tile_img(self, tile):
        return self.get_cached_img(tile, self.img_cache, self.img)
        
    def get_mask_img(self, tile):
        if self.mask is None:
            return None
        return self.get_cached_img(tile, self.mask_cache, self.mask)
