from __future__ import division
import pygame
import sys

def topygame(img):
    return pygame.image.frombuffer(img.tostring(), img.size, "RGB")

def draw(img, box):
    screen.blit(topygame(img), box)

def draw_scaled(filename, x,y,w,h):
    screen.blit(pygame.transform.scale(pygame.image.load(filename), (w, h)), (x,y))

def crop_to_fit(img, tile_size):
    "Return a copy of img cropped to precisely fill the dimesions tile_size."
    img_w, img_h = img.get_width(), img.get_height()
    tile_w, tile_h = tile_size
    img_aspect = img_w/img_h
    tile_aspect = tile_w/tile_h

    if img_aspect > tile_aspect:
        # It's too wide.
        crop_h = tile_h
        crop_w = int(round(crop_h*img_aspect))
        x_offset = abs(int((tile_w - crop_w)/2))
        y_offset = 0
    else:
        # It's too tall.
        crop_w = tile_w
        crop_h = int(round(crop_w/img_aspect))
        x_offset = 0
        y_offset = abs(int((tile_h - crop_h)/2))
   
    scaled = pygame.transform.scale(img, (crop_w, crop_h))
    return scaled, x_offset, y_offset

class MosaicGUI:
    def __init__(self, size):
        pygame.init()
        self.screen = pygame.display.set_mode(size)

    def draw(self):
        pygame.display.flip()
        
    def rectangle(self, color, coords, width=0):
        pygame.draw.rect(self.screen, color, coords, width)    
        
    def img(self, image, box):
        self.screen.blit(topygame(image), box)
        
    def scaled_img(self, filename, x,y,w,h):
        scaled, x0, y0 = crop_to_fit(pygame.image.load(filename), (w, h))
        self.screen.blit(scaled, (x,y), (x0,y0,w,h))

    def wait_for_close(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: sys.exit()
