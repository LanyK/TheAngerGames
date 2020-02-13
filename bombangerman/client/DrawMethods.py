import pygame
from Sprites import Charsheet


def color_sprite(surface, color):
    """ Returns a colored copy (!) of the sprite/surface.
    """
    surface = surface.copy()  # dont change the spritesheet's sprite!
    arr = pygame.surfarray.pixels3d(surface)  # references the points via numpy
    arr[:, :, 0] = color[0]  # red
    arr[:, :, 1] = color[1]  # green
    arr[:, :, 2] = color[2]  # blue
    return surface

def color_change(surface):
    # TODO: this is just swaps red and blue channel -> there is certainly a better solution
    surface = surface.copy()
    arr = pygame.surfarray.pixels3d(surface)
    arr[:, :, 0] = arr[:, :, 2]
    arr[:, :, 1] = arr[:, :, 1]
    arr[:, :, 2] = arr[:, :, 0]
    return surface

class BarDrawer(object):
    """ Singleton class to be used statically: BarDrawer.draw(..)
    """

    @classmethod
    def draw(cls, surface, position, bar_height=16, full_bar_width=80, fill_percent=1, color=(255, 255, 255)):
        """ Draws a horizontal bar in the given color on the provided surface.

            :param surface: The pygame surface to draw onto
            :param position: The upper left corner of the bar
            :param bar_height: The height of the bar in pixels
            :param full_bar_width: The width of the bar in pixels when at 100%
            :param fill_percent: The current filling status of the bar. 0.5 will half the bar's width.
            :param color: tuple of (r,g,b). Defaults to white.
        """

        pygame.draw.rect(surface, color,
                         pygame.Rect(position[0], position[1], int(full_bar_width * fill_percent), bar_height))


class TextDrawer(object):
    """ Singleton class to be used statically: TextDrawer.draw(..)
        Text can contain newlines and ASCII. Tabs are converted to 4 spaces.
    """

    @classmethod
    def draw(cls, charsheet: Charsheet, screen, position, text, horizontal_spacing=0, color=None):
        """ :param charsheet: A Charsheet instance that supports get_sprite and get_spacing
            :param screen: The pygame screen to draw onto
            :param position: The (x,y) position to begin drawing to
            :param text: The text to draw. ASCII only.
            :param horizontal_spacing: Optional horizontal spacing between characters. May be negative.
            :param color: Optional (r,g,b) color information to color the text. Default is set by the underlying spritesheet.
        """
        if not isinstance(text,str):
            # print("[WARNING] Non str type object given to TextDrawer as text argument. Using str(..) on it.")
            text = str(text)
        text = text.replace("\t", "    ")
        size = (0, 0)
        initial_x = position[0]
        for c in text:
            if c == "\n":
                position = (initial_x, position[1] + size[1])
            else:
                sprite_id = ord(c) - 32
                sprite, size = charsheet.get_sprite(sprite_id)
                char_spacing = charsheet.get_spacing(sprite_id)

                if color != None:
                    sprite = color_sprite(sprite, color)

                screen.blit(sprite, position)
                position = (position[0] + size[0] + horizontal_spacing + char_spacing, position[1])
