# -*- coding: utf-8 -*-
"""Contains user API for PyPDFForm."""

from __future__ import annotations

from typing import BinaryIO, Dict, Union

from .core import filler, font
from .core import image as image_core
from .core import utils
from .core import watermark as watermark_core
from .middleware import adapter, constants
from .middleware import template as template_middleware
from .middleware.dropdown import Dropdown
from .middleware.text import Text


class Wrapper:
    """A class to represent a PDF form."""

    def __init__(
        self,
        template: Union[bytes, str, BinaryIO] = b"",
        **kwargs,
    ) -> None:
        """Constructs all attributes for the object."""

        self.stream = adapter.fp_or_f_obj_or_stream_to_stream(template)
        self.elements = (
            template_middleware.build_elements(self.stream) if self.stream else {}
        )

        for each in self.elements.values():
            if isinstance(each, Text):
                each.font = kwargs.get("global_font", constants.GLOBAL_FONT)
                each.font_size = kwargs.get("global_font_size")
                each.font_color = kwargs.get(
                    "global_font_color", constants.GLOBAL_FONT_COLOR
                )

    def read(self) -> bytes:
        """Reads the file stream of a PDF form."""

        return self.stream

    def __add__(self, other: Wrapper) -> Wrapper:
        """Overloaded addition operator to perform merging PDFs."""

        if not self.stream:
            return other

        if not other.stream:
            return self

        new_obj = self.__class__()
        new_obj.stream = utils.merge_two_pdfs(self.stream, other.stream)

        return new_obj

    def fill(
        self,
        data: Dict[str, Union[str, bool, int]],
    ) -> Wrapper:
        """Fill a PDF form."""

        for key, value in data.items():
            if key in self.elements:
                self.elements[key].value = value

        for key, value in self.elements.items():
            if isinstance(value, Dropdown):
                self.elements[key] = template_middleware.dropdown_to_text(value)

        utils.update_text_field_attributes(self.stream, self.elements)
        if self.read():
            self.elements = template_middleware.set_character_x_paddings(
                self.stream, self.elements
            )

        self.stream = utils.remove_all_elements(filler.fill(self.stream, self.elements))

        return self

    def draw_text(
        self,
        text: str,
        page_number: int,
        x: Union[float, int],
        y: Union[float, int],
        **kwargs,
    ) -> Wrapper:
        """Draws a text on a PDF form."""

        new_element = Text("new")
        new_element.value = text
        new_element.font = kwargs.get("font", constants.GLOBAL_FONT)
        new_element.font_size = kwargs.get("font_size", constants.GLOBAL_FONT_SIZE)
        new_element.font_color = kwargs.get("font_color", constants.GLOBAL_FONT_COLOR)

        watermarks = watermark_core.create_watermarks_and_draw(
            self.stream,
            page_number,
            "text",
            [
                [
                    new_element,
                    x,
                    y,
                ]
            ],
        )

        self.stream = watermark_core.merge_watermarks_with_pdf(self.stream, watermarks)

        return self

    def draw_image(
        self,
        image: Union[bytes, str, BinaryIO],
        page_number: int,
        x: Union[float, int],
        y: Union[float, int],
        width: Union[float, int],
        height: Union[float, int],
        rotation: Union[float, int] = 0,
    ) -> Wrapper:
        """Draws an image on a PDF form."""

        image = adapter.fp_or_f_obj_or_stream_to_stream(image)
        image = image_core.any_image_to_jpg(image)
        image = image_core.rotate_image(image, rotation)
        watermarks = watermark_core.create_watermarks_and_draw(
            self.stream, page_number, "image", [[image, x, y, width, height]]
        )

        self.stream = watermark_core.merge_watermarks_with_pdf(self.stream, watermarks)

        return self

    def generate_schema(self) -> dict:
        """Generates a json schema for the PDF form template."""

        result = {
            "type": "object",
            "properties": {
                key: value.schema_definition for key, value in self.elements.items()
            },
        }

        return result

    @classmethod
    def register_font(
        cls, font_name: str, ttf_file: Union[bytes, str, BinaryIO]
    ) -> bool:
        """Registers a font from a ttf file."""

        ttf_file = adapter.fp_or_f_obj_or_stream_to_stream(ttf_file)

        return (
            font.register_font(font_name, ttf_file) if ttf_file is not None else False
        )
