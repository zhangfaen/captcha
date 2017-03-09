# coding: utf-8
"""
    captcha.image
    ~~~~~~~~~~~~~
    Generate Image CAPTCHAs, just the normal image CAPTCHAs you are using.
"""

import math
import os
import random

from PIL import Image
from PIL import ImageFilter
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
DEFAULT_FONTS = [os.path.join(DATA_DIR, 'DroidSansMono.ttf')]

__all__ = ['ImageCaptcha']

table = []
for i in range(256):
    table.append(i * 1.97)


class _Captcha(object):
    def generate(self, chars, format='png'):
        """Generate an Image Captcha of the given characters.
        :param chars: text to be generated.
        :param format: image file format
        """
        im = self.generate_image(chars)
        out = BytesIO()
        im.save(out, format=format)
        out.seek(0)
        return out

    def write(self, chars, output, format='png'):
        """Generate and write an image CAPTCHA data to the output.
        :param chars: text to be generated.
        :param output: output destionation.
        :param format: image file format
        """
        im = self.generate_image(chars)
        return im.save(output, format=format)

class ImageCaptcha(_Captcha):
    """Create an image CAPTCHA.
    Many of the codes are borrowed from wheezy.captcha, with a modification
    for memory and developer friendly.
    ImageCaptcha has one built-in font, DroidSansMono, which is licensed under
    Apache License 2. You should always use your own fonts::
        captcha = ImageCaptcha(fonts=['/path/to/A.ttf', '/path/to/B.ttf'])
    You can put as many fonts as you like. But be aware of your memory, all of
    the fonts are loaded into your memory, so keep them a lot, but not too
    many.
    :param width: The width of the CAPTCHA image.
    :param height: The height of the CAPTCHA image.
    :param fonts: Fonts to be used to generate CAPTCHA images.
    :param font_sizes: Random choose a font size from this parameters.
    """

    def __init__(self, width=180, height=60, fonts=None, font_sizes=None):
        self._width = width
        self._height = height
        self._fonts = fonts or DEFAULT_FONTS
        self._font_sizes = font_sizes or (38, 46, 49)
        self._truefonts = []

    @property
    def truefonts(self):
        if self._truefonts:
            return self._truefonts
        self._truefonts = tuple([
                                    truetype(n, s)
                                    for n in self._fonts
                                    for s in self._font_sizes
                                    ])
        return self._truefonts

    @staticmethod
    def arc(draw, bbox, start, end, fill, width=1, segments=100):
        """
        Hack that looks similar to PIL's draw.arc(), but can specify a line width.
        """
        # radians
        start *= math.pi / 180
        end *= math.pi / 180

        # angle step
        da = (end - start) / segments

        # shift end points with half a segment angle
        start -= da / 2
        end -= da / 2

        # ellips radii
        rx = (bbox[2] - bbox[0]) / 2
        ry = (bbox[3] - bbox[1]) / 2

        # box centre
        cx = bbox[0] + rx
        cy = bbox[1] + ry

        # segment length
        l = (rx + ry) * da / 2.0

        for i in range(segments):
            # angle centre
            a = start + (i + 0.5) * da

            # x,y centre
            x = cx + math.cos(a) * rx
            y = cy + math.sin(a) * ry

            # derivatives
            dx = -math.sin(a) * rx / (rx + ry)
            dy = math.cos(a) * ry / (rx + ry)

            draw.line([(x - dx * l, y - dy * l), (x + dx * l, y + dy * l)], fill=fill, width=width)

    @staticmethod
    def create_noise_curve(image, color):
        w, h = image.size
        x1 = random.randint(0, int(w / 10))
        x2 = random.randint(w - int(w / 10), w)
        y1 = random.randint(h / 10, h - int(h / 10))
        y2 = random.randint(y1, h - int(h / 10))

        points = [(x1, y1), (x2, y2)]
        end = random.randint(150, 200)
        start = random.randint(0, 50)
        # the default arc method does not support to modify width
        # Draw(image).arc(points, start, end, fill=color)
        bbox = [x1, y1, x2, y2]
        ImageCaptcha.arc(Draw(image), bbox, start, end, color, 10, 100)
        return image

    @staticmethod
    def create_noise_dots(image, color, width=3, number=80):
        draw = Draw(image)
        w, h = image.size
        while number:
            x1 = random.randint(0, w)
            y1 = random.randint(0, h)
            draw.line(((x1, y1), (x1 - 1, y1 - 1)), fill=color, width=width)
            number -= 1
        return image

    def create_captcha_image(self, chars, color, background):
        """Create the CAPTCHA image itself.
        :param chars: text to be generated.
        :param color: color of the text.
        :param background: color of the background.
        The color should be a tuple of 3 numbers, such as (0, 255, 255).
        """
        image = Image.new('RGB', (self._width, self._height), background)
        draw = Draw(image)

        def _draw_character(c):
            font = random.choice(self.truefonts)
            w, h = draw.textsize(c, font=font)

            dx = random.randint(0, 4)
            dy = random.randint(0, 6)
            im = Image.new('RGBA', (w + dx, h + dy))
            Draw(im).text((dx, dy), c, font=font, fill=color)

            # rotate
            im = im.crop(im.getbbox())
            im = im.rotate(random.uniform(-30, 30), Image.BILINEAR, expand=1)

            # warp
            dx = w * random.uniform(0.1, 0.3)
            dy = h * random.uniform(0.2, 0.3)
            x1 = int(random.uniform(-dx, dx))
            y1 = int(random.uniform(-dy, dy))
            x2 = int(random.uniform(-dx, dx))
            y2 = int(random.uniform(-dy, dy))
            w2 = w + abs(x1) + abs(x2)
            h2 = h + abs(y1) + abs(y2)
            data = (
                x1, y1,
                -x1, h2 - y2,
                w2 + x2, h2 + y2,
                w2 - x2, -y1,
            )
            im = im.resize((w2, h2))
            im = im.transform((w, h), Image.QUAD, data)
            return im

        images = []
        for c in chars:
            images.append(_draw_character(c))

        text_width = sum([im.size[0] for im in images])

        if text_width > self._width:
            print text_width, self._width
        width = max(text_width, self._width)
        image = image.resize((width, self._height))

        average = int(text_width / len(chars))
        rand = int(0.25 * average)
        offset = int(average * 0.1)

        for im in images:
            w, h = im.size
            mask = im.convert('L').point(table)
            image.paste(im, (offset, int((self._height - h) / 2)), mask)
            offset = offset + w + random.randint(-rand, 0)

        return image

    def generate_image(self, chars):
        """Generate the image of the given characters.
        :param chars: text to be generated.
        """
        background = random_color(238, 255)
        color = random_color(0, 200, random.randint(220, 255))
        im = self.create_captcha_image(chars, color, background)
        # we could comment the two lines if noise is not needed
        self.create_noise_dots(im, color)
        self.create_noise_curve(im, color)
        im = im.filter(ImageFilter.SMOOTH)
        return im


def random_color(start, end, opacity=None):
    red = random.randint(start, end)
    green = random.randint(start, end)
    blue = random.randint(start, end)
    if opacity is None:
        return (red, green, blue)
    return (red, green, blue, opacity)
