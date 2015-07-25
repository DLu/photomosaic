# Copyright 2012 Daniel B. Allan
# dallan@pha.jhu.edu, daniel.b.allan@gmail.com
# http://pha.jhu.edu/~dallan
# http://www.danallan.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses>.

from __future__ import division
import logging
import random
import numpy as np
from PIL import Image
from progress_bar import progress_bar
from sql_image_pool import SqlImagePool
from tile import Tile
from image_functions import *
from partition import *
from image_analysis import *

# Configure logger.
FORMAT = "%(name)s.%(funcName)s:  %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

def simple(image_dir, target_filename, dimensions, output_file):
    "A convenient wrapper for producing a traditional photomosaic."
    pool = SqlImagePool('temp.db')
    pool.add_directory(image_dir)
    
    p = Photomosaic(target_filename, pool)
    p.partition_tiles(dimensions)
    p.match()
    p.assemble()
    p.save(output_file)
    
    pool.close()
    
class Photomosaic:
    def __init__(self, target_filename, pool, mask=None, tuning=True):
        self.orig_img = open(target_filename)
        self.pool = pool
        self.tuning = tuning
        self.set_mask(mask)
        if tuning:
            self.img = self.tune(quiet=True)
        else:    
            self.img = self.orig_img
        self.tiles = None
        self.mos = None
        
    def partition_tiles(self, dimensions=10, depth=0, hdr=80,
              debris=False, min_debris_depth=1, analyze=True):
        "Partition the target image into a list of Tile objects."
        self.p = Partition(self.img)
        self.p.simple_partition(dimensions, depth, hdr, debris, 
            min_debris_depth, analyze)
            
        self.numbers = {}    

        if not analyze:
            return
        pbar = progress_bar(len(self.p.tiles), "Analyzing images")
        for tile in self.p.tiles:
            self.numbers[tile] = analyze_this( self.p.get_tile_img(tile) )
            pbar.next()

    def match(self, tolerance=1, usage_penalty=1, usage_impunity=2):
        """Assign each tile a new image, and open that image in the Tile object."""
        if len(self.pool)==0:
            logger.error('No images in pool to match!')
            exit(-1)
        self.pool.reset_usage()
        
        self.matches = {}
        
        pbar = progress_bar(len(self.p.tiles), "Choosing and loading matching images")
        for tile in self.p.tiles:
            #if tile.blank:
            #    pbar.next()
            #    continue
            self.match_one(tile, tolerance, usage_penalty, usage_impunity)
            pbar.next()
    
    def match_one(self, tile, tolerance=1, usage_penalty=1, usage_impunity=2):
        rgb, lab = self.numbers[ tile ] 
        match = self.pool.choose_match(lab, tolerance, usage_penalty )
        self.matches[ tile ] = match
        print 'MATCH', match
            
    def assemble(self, pad=False, scatter=False, margin=0, scaled_margin=False,
           background=(255, 255, 255)):
        """Create the mosaic image.""" 
        # Infer dimensions so they don't have to be passed in the function call.
        mosaic_size = map(max, zip(*[(tile[0]+tile[2], tile[1]+tile[3]) for tile in self.p.tiles]))
        mos = Image.new('RGB', mosaic_size, background)
        pbar = progress_bar(len(self.p.tiles), "Scaling and placing tiles")
        random.shuffle(self.p.tiles)
        for tile in self.p.tiles:
            #if tile.blank:
            #    pbar.next()
            #    continue
            if pad:
                size = shrink_by_lightness(pad, tile.size, tile.match['dL'])
                if margin == 0:
                    margin = min(tile.size[0] - size[0], tile.size[1] - size[1])
            else:
                size = tile[2], tile[3]
            if scaled_margin:
                pos = tile.get_position(size, scatter, margin//(1 + tile.depth))
            else:
                pos = tile[0], tile[1] #tile.get_position(size, scatter, margin)
                
            fn = self.matches[tile][4]
            mi = Image.open(fn) 
            mos.paste(crop_to_fit(mi, size), pos)
            pbar.next()
        self.mos = mos
        
    def save(self, output_file):
        if self.tuning:
            mos = self.untune()
        else:
            mos = self.mos
                
        logger.info('Saving mosaic to %s', output_file)
        mos.save(output_file)
        
    def set_mask(self, mask_fn):
        if mask_fn:
            self.mask = open(mask_fn)
            self.m = crop_to_fit(self.mask, self.orig_img.size)
            self.target_palette = compute_palette(img_histogram(self.orig_img, self.m))
        else:
            self.mask = None
            self.m = None
            self.target_palette = compute_palette(img_histogram(self.orig_img))
        

    def tune(self, quiet=True):
        """Adjust the levels of the image to match the colors available in the
        the pool. Return the adjusted image. Optionally plot some histograms."""
        if len(self.pool)==0:
            return self.orig_img
        pool_hist = self.pool.pool_histogram()
        pool_palette = compute_palette(pool_hist)
        
        adjusted_img = adjust_levels(self.orig_img, self.target_palette, pool_palette)
        
        if not quiet:
            # Use the Image.histogram() method to examine the target image
            # before and after the alteration.
            keys = 'red', 'green', 'blue'
            values = [channel.histogram() for channel in self.orig_img.split()]
            totals = map(sum, values)
            norm = [map(lambda x: 256*x/totals[i], val) \
                    for i, val in enumerate(values)]
            orig_hist = dict(zip(keys, norm)) 
            values = [channel.histogram() for channel in adjusted_img.split()]
            totals = map(sum, values)
            norm = [map(lambda x: 256*x/totals[i], val) \
                    for i, val in enumerate(values)]
            adjusted_hist = dict(zip(keys, norm)) 
            plot_histograms(pool_hist, title='Images in the pool')
            plot_histograms(orig_hist, title='Unaltered target image')
            plot_histograms(adjusted_hist, title='Adjusted target image')
        return adjusted_img
        
    def untune(self, amount=1):
        if self.mask:
            img_palette = compute_palette(img_histogram(self.img, m))
        else:    
            img_palette = compute_palette(img_histogram(self.img))
        return Image.blend(self.mos, adjust_levels(self.mos, img_palette, self.target_palette), amount)


def assemble_tiles(tiles, margin=1):
    """This is not used to build the final mosaic. It's a handy function for
    assembling new tiles (without blanks) to see how partitioning looks."""
    # Infer dimensions so they don't have to be passed in the function call.
    dimensions = map(max, zip(*[(1 + tile.x, 1 + tile.y) for tile in tiles]))
    mosaic_size = map(lambda (x, y): x*y,
                         zip(*[tiles[0].ancestor_size, dimensions]))
    background = (255, 255, 255)
    mos = Image.new('RGB', mosaic_size, background)
    for tile in tiles:
        if tile.blank:
            continue
        shrunk = tile.size[0]-2*int(margin), tile.size[1]-2*int(margin)
        pos = tile.get_position(tile, shrunk, False, 0)
        mos.paste(tile.resize(shrunk), pos)
    return mos
