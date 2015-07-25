from __future__ import division
from image_functions import *
from math import floor, ceil

FORMAT = "%(name)s.%(funcName)s:  %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

class Partition:
    def __init__(self, img, mask=None):
        self.img = img
        self.mask = mask
        self.areas = []
        self.tiles = None

    def simple_partition(self, dimensions=10, depth=0, hdr=80,
              debris=False, min_debris_depth=1, analyze=True):
        "Partition the target image into a list of Tile objects."
        if isinstance(dimensions, int):
            dimensions = dimensions, dimensions

        mask = self.mask
        
        #if mask:
        #    mask = crop_to_fit(mask, new_size)
        #    if not debris:
        #        mask = mask.convert("1") # no gray
        width = self.img.size[0] / dimensions[0] 
        height = self.img.size[1] / dimensions[1]

        for y in range(dimensions[1]):
            for x in range(dimensions[0]):
                self.areas.append( (x*width, y*height, width, height) )

        """
        for g in xrange(depth):
            old_tiles = tiles
            tiles = []
            for tile in old_tiles:
                if tile.dynamic_range() > hdr or tile.straddles_mask_edge():
                    # Keep children; discard parent.
                    tiles += tile.procreate()
                else:
                    # Keep tile -- no children.
                    tiles.append(tile)
            logging.info("There are %d tiles in generation %d",
                         len(tiles), g)
        # Now that all tiles have been made and subdivided, decide which are blank.
        [tile.determine_blankness(min_debris_depth) for tile in tiles]
        logger.info("%d tiles are set to be blank",
                    len([1 for tile in tiles if tile.blank]))"""
        
        """
        if not analyze:
            return
        pbar = progress_bar(len(self.tiles), "Analyzing images")
        for tile in self.tiles:
            tile.analyze()
            pbar.next()"""
        self.get_tiles()    
    
    def get_tiles(self):
        if self.tiles:
            return self.tiles
        self.tiles = []    
        for x,y,w,h in self.areas:    
            x0 = int(floor(x))
            y0 = int(floor(y))
            w0 = int(ceil(x+w)-x0)
            h0 = int(ceil(y+h)-y0)
            self.tiles.append( (x0, y0, w0, h0) )                    

    def get_tile_img(self, tile):
        (x,y,w,h) = tile
        return self.img.crop((x, y, x+w, y+h))
        
