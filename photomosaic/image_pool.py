from directory_walker import DirectoryWalker
from progress_bar import progress_bar
import color_spaces as cs
from PIL import Image
from image_functions import *
from image_analysis import analyze_this
import logging

# Configure logger.
FORMAT = "%(name)s.%(funcName)s:  %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

class ImagePool:
    def __init__(self):
        None

    def add_directory(self, image_dir, skip_errors=True):
        walker = DirectoryWalker(image_dir)
        file_count = len(list(walker)) # stupid but needed but progress bar
        pbar = progress_bar(file_count, "Analyzing images and building db")

        for filename in walker:
            self.add_image(filename, skip_errors)
            pbar.next()
        logger.info('Collection %s built with %d images'%(self.db_name, len(self)))
        
    def add_image(self, filename, skip_errors=False):
        if filename in self:
            logger.warning("Image %s is already in the table. Skipping it."%filename)
            return
            
        try:
            img = Image.open(filename)
        except IOError:
            logger.warning("Cannot open %s as an image. Skipping it.",
                           filename)
            return
            
        if img.mode != 'RGB':
            logger.warning("RGB images only. Skipping %s.", filename)
            return
            
        w, h = img.size
        try:
            rgb, lab = analyze_this(img)
        except Exception as e:
            logger.warning("Unknown problem analyzing %s. (%s) Skipping it.",
                           filename, str(e))
            if not skip_errors:
                raise
        self.insert(filename, w, h, rgb, lab)
        return
