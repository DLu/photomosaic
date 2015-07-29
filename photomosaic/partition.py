from __future__ import division
from image_functions import *
from math import floor, ceil
from random import randrange

FORMAT = "%(name)s.%(funcName)s:  %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

class Tile:
    def __init__(self, x,y,w,h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
    
    def is_float(self):
        return type(self.x)==float
        
    def int_version(self):
        x0 = int(floor(self.x))
        y0 = int(floor(self.y))
        w0 = int(ceil(self.x+self.w)-x0)
        h0 = int(ceil(self.y+self.h)-y0)
        return Tile(x0,y0,w0,h0)
        
    def quad(self):
        return (self.x, self.y, self.w, self.h)
        
    def coords(self):
        return (self.x, self.y, self.x+self.w, self.y+self.h)
        
    def __hash__(self):
        return hash(self.quad())

    def __eq__(self, other):
        return self.quad() == other.quad()

def procreate(tile):
    """Divide image into quadrants, and return them all in a list.""" 
    x,y,w,h = tile.quad()
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
        self.tiles = []
        self.final_tiles = None
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
                self.tiles.append( Tile(x*width, y*height, width, height) )

    def brick_partition(self, dimensions=10):
        if isinstance(dimensions, int):
            dimensions = dimensions, dimensions

        width = self.img.size[0] / dimensions[0] 
        height = self.img.size[1] / dimensions[1]

        for y in range(dimensions[1]):
            if y%2==0:
                for x in range(dimensions[0]):
                    self.tiles.append( Tile(x*width, y*height, width, height) )
            else:
                for x in range(dimensions[0]-1):
                    self.tiles.append( Tile(x*width+width/2, y*height, width, height) )
                self.tiles.append( Tile(0, y*height, width/2, height) )    
                self.tiles.append( Tile(self.img.size[0]-width/2, y*height, width/2, height) )    

    def recursive_split(self, depth=0, hdr=80):
        for g in xrange(depth):
            old_tiles = self.tiles
            self.tiles = []
            for tile in old_tiles:
                im = self.get_tile_img(tile)
                if dynamic_range(im) > hdr or self.straddles_mask_edge(tile):
                    # Keep children; discard parent.
                    self.tiles += procreate(tile)
                else:
                    # Keep tile -- no children.
                    self.tiles.append(tile)
            logging.info("There are %d tiles in generation %d",
                         len(self.tiles), g)

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
        for tile in self.tiles:
            mtile = self.get_mask_img(tile)
            brightest_pixel = mtile.getextrema()[1]
            if brightest_pixel == 255:
                new_tiles.append( tile )
            elif brightest_pixel == 0:
                continue
            elif tile.w >= max_size * self.img.size()[0]:
                continue
            elif rand_range(255) < brightest_pixel:
                new_tiles.append( tile )
            
        logger.info("%d/%d tiles are set to be blank",
                    len(self.tiles)-len(new_tiles), len(self.tiles))
        self.tiles = new_tiles

    def get_tiles(self):
        if self.final_tiles:
            return self.final_tiles
        self.remove_blanks()
        self.final_tiles = map(Tile.int_version, self.tiles)
        return self.final_tiles

    def get_cached_img(self, tile, cache, img):
        if tile.is_float():
            tile = tile.int_version()

        if tile not in cache:
            cache[tile] = img.crop( tile.coords() )

        return cache[tile]

    def get_tile_img(self, tile):
        return self.get_cached_img(tile, self.img_cache, self.img)
        
    def get_mask_img(self, tile):
        if self.mask is None:
            return None
        return self.get_cached_img(tile, self.mask_cache, self.mask)
