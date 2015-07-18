from __future__ import division
from image_functions import *

FORMAT = "%(name)s.%(funcName)s:  %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

class Partition:
    def __init__(self, img, mask=None):
        self.img = img
        self.mask = mask
        self.new_img = None
        self.areas = []

    def simple_partition(self, dimensions=10, depth=0, hdr=80,
              debris=False, min_debris_depth=1, base_width=None, analyze=True):
        "Partition the target image into a list of Tile objects."
        if isinstance(dimensions, int):
            dimensions = dimensions, dimensions
        if base_width is not None:
            cwidth = self.img.size[0] / dimensions[0]
            width = base_width * dimensions[0]
            factor = base_width / cwidth
            height = int(self.img.size[1] * factor)
            print self.img.size, dimensions, width, height
            img = crop_to_fit(self.img, (width, height))
        # img.size must have dimensions*2**depth as a factor.
        factor = dimensions[0]*2**depth, dimensions[1]*2**depth
        new_size = tuple([int(factor[i]*np.ceil(self.img.size[i]/factor[i])) \
                          for i in [0, 1]])
        logger.info("Resizing image to %s, a round number for partitioning. "
                    "If necessary, I will crop to fit.",
                    new_size)
        img = crop_to_fit(self.img, new_size)
        
        mask = self.mask
        
        if mask:
            mask = crop_to_fit(mask, new_size)
            if not debris:
                mask = mask.convert("1") # no gray
        width = img.size[0] // dimensions[0] 
        height = img.size[1] // dimensions[1]
        tiles = []
        for y in range(dimensions[1]):
            for x in range(dimensions[0]):
                tiles.append( (x*width, y*height, width, height) )

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
        self.new_img = img            
        self.tiles = tiles
        
        """
        if not analyze:
            return
        pbar = progress_bar(len(self.tiles), "Analyzing images")
        for tile in self.tiles:
            tile.analyze()
            pbar.next()"""
            
    def get_tile_img(self, tile):
        (x,y,w,h) = tile
        return self.new_img.crop((x, y, x+w, y+h))
        
