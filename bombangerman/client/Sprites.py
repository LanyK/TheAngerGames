import pygame
import json
from collections import defaultdict

class Spritesheet(object):

    @classmethod
    def from_file(cls, filename, sprite_size=(16, 16)):
        """ @param sprite_size: Defaults to (16,16)

            Load a spritesheet from a file.

            This method will load an image file and cut it into a list of pygame images by moving horizontally through the file. If the spritesheet file contains more than one line of images as definied by the comparison of the image size and the sprite_size parameter, the list will be filled row by row from the source image.
        """
        try:
            image = pygame.image.load(filename).convert_alpha()
            name = filename
            size = image.get_size()  # (int,int)
            sprites = []
            current_x = 0
            current_y = 0

            # Check spritesheet cutting operation validity
            if sprite_size[0] > size[0] or sprite_size[1] > size[1]:
                raise KeyError("Trying to create a spritesheet from an image smaller than the desired sprite_size:",
                               sprite_size, "out of", size)

            # Cut spritesheet to gather sprites
            for row in range(0, size[1] // sprite_size[1]):
                for column in range(0, size[0] // sprite_size[0]):
                    top_left = (column * sprite_size[0], row * sprite_size[1])
                    sprite = Spritesheet.get_image_from_rect(image,
                                                             (top_left[0], top_left[1], sprite_size[0], sprite_size[1]))
                    sprites.append(sprite)

            return Spritesheet.from_image_list(sprites, name)

        except pygame.error as e:
            print("Error when trying to load image:", filename)
            raise e

    @classmethod
    def from_image_list(cls, image_list, name):
        """ Create a new Spritesheet from a list of pygame images """
        return cls(name, image_list)

    def __init__(self, name, sprites):
        self.name = name
        self.sprites = sprites

    @classmethod
    def get_image_from_rect(cls, source_image, rectangle, colorkey=None):
        """ Extract a new sprite image from the spritesheet

            @param source_image: the image to crop from
            @param rectangle: Loads sprite from rectangle (x,y,x+offset,y+offset)
            @param colorkey: Optional colorkey for image.set_colorkey(..)
        """
        rect = pygame.Rect(rectangle)
        image = pygame.Surface(rect.size, pygame.SRCALPHA).convert_alpha()
        image.blit(source_image, (0, 0), rect)
        if colorkey is not None:
            if colorkey is -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)
        return image

    def __len__(self):
        return len(self.sprites)

    def __str__(self):
        return "<Spritesheet " + str(self.name) + " (len:" + str(len(self)) + ")>"

    def num_sprites(self):
        return len(self)

    def get_sprites(self, index_list):
        """ Returns a list of sprites. Equivalent to calling get_sprite multiple times.
        """
        return [self.get_sprite(index) for index in index_list]

    def get_sprite(self, index):
        """ Returns the ith sprite in the spritesheet and it's size (x,y)
        """
        try:
            sprite = self.sprites[index]
        except IndexError as e:
            print("Tried to get value at index", index, "in a spritesheet of length", len(self))
            raise e
        return sprite, sprite.get_size()


class Charsheet():
    """ Is a spritesheet wrapper that can hold a horizontal spacing map dictionary that maps sprite_id to horizontal pixel offsets. Use to smoothen text rendering on variable width character fonts.
    The mapping can be partial, will default to 0 pixels for unspecified sprite_id values. """

    def __init__(self, spritesheet, spacing=None):
        self.horizontal_spacing_map = spacing if spacing else dict()
        self.spritesheet = spritesheet

    def load_spacing_map(self, file_name):
        """ expects a json dictionary """
        with open(file_name) as fh:
            self.horizontal_spacing_map = json.loads(fh.read())

    def get_spacing(self, sprite_id):
        """ Horizontal offset in pixels, can be negative """
        return self.horizontal_spacing_map.get(str(sprite_id), 0)

    def get_sprite(self, index):
        return self.spritesheet.get_sprite(index)

    def num_sprites(self):
        return len(self)

    def __len__(self):
        return len(self.spritesheet)

    def __str__(self):
        return "<Charsheet " + str(self.spritesheet.name) + " (len:" + str(len(self)) + ")>"


class Animation(object):
    """ An animation object points to a list of sprites along with timing information.
        The animation can be advanced and will return the current sprite when asked.
    """

    def __init__(self, sprites, timing_dict):
        """ :param sprites: List of Sprites (pygame surfaces) or Spritesheet instance
            :param timing_dict: Dict mapping of animation frame index to tick count;
                                Frames not specified default to 1 tick.
        """
        self.frames = sprites if not isinstance(sprites, Spritesheet) else sprites.sprites
        self.timing_dict = defaultdict(lambda: 1)
        self.timing_dict.update(timing_dict)
        self.current_time_step = 0
        self.total_time_steps = sum(self.timing_dict[frame_idx] for frame_idx in range(len(self.frames)))
        self.timing_to_frame_map = dict()
        next_time_step = 0
        for frame_idx, frame in enumerate(self.frames):
            time_steps_for_frame = self.timing_dict[frame_idx]
            for step in range(time_steps_for_frame):
                self.timing_to_frame_map[next_time_step] = frame_idx
                next_time_step += 1

    def get_next_frame(self):
        """ Returns the next frame (sprite/surface) and advances the animation
        """
        sprite = self.frames[self.timing_to_frame_map[self.current_time_step]]
        self.current_time_step += 1
        if self.current_time_step == self.total_time_steps:
            self.current_time_step = 0
        return sprite

    def reset_animation(self):
        """ Resets the animation to the first time step
        """
        self.current_time_step = 0

    def shallow_copy(self):
        """ returns an independent animation instance pointing to the same sprite instances.
        """
        return Animation(self.sprites, self.timing_dict)
