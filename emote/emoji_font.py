import ctypes
import os
from pathlib import Path
from xml.sax.saxutils import escape

import gi

gi.require_version("PangoCairo", "1.0")
from gi.repository import PangoCairo

from emote import config

BUNDLED_FAMILY = "Emote Emoji"
_fontconfig = None
_registered = False
_alias_loaded = False


def create_font_map(choice):
    global _fontconfig, _registered, _alias_loaded
    bundled = False
    try:
        if choice == "system" and not _registered:
            return PangoCairo.FontMap.new(), False
        if _fontconfig is None:
            _fontconfig = ctypes.CDLL("libfontconfig.so.1")
            _fontconfig.FcConfigGetCurrent.restype = ctypes.c_void_p
            _fontconfig.FcConfigParseAndLoadFromMemory.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_int,
            ]
            _fontconfig.FcConfigParseAndLoadFromMemory.restype = ctypes.c_int
            _fontconfig.FcConfigAppFontAddFile.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
            ]
            _fontconfig.FcConfigAppFontAddFile.restype = ctypes.c_int
            _fontconfig.FcConfigAppFontClear.argtypes = [ctypes.c_void_p]
            _fontconfig.FcConfigAppFontClear.restype = None
        current = _fontconfig.FcConfigGetCurrent()
        if not current:
            raise RuntimeError("Fontconfig has no active configuration")
        if choice == "system":
            _fontconfig.FcConfigAppFontClear(current)
            _registered = False
        else:
            if not _registered:
                path = (Path(config.static_dir) / "fonts/NotoColorEmoji.ttf").resolve()
                if not path.is_file():
                    raise FileNotFoundError(path)
                if not _alias_loaded:
                    # A private family avoids picking an older system Noto font.
                    xml = (
                        '<fontconfig><match target="scan">'
                        '<test name="file" compare="eq">'
                        f"<string>{escape(str(path))}</string></test>"
                        '<edit name="family" mode="assign">'
                        f"<string>{BUNDLED_FAMILY}</string></edit>"
                        "</match></fontconfig>"
                    )
                    if not _fontconfig.FcConfigParseAndLoadFromMemory(
                        current, xml.encode(), 1
                    ):
                        raise RuntimeError(
                            "Fontconfig could not register the font family"
                        )
                    _alias_loaded = True
                if not _fontconfig.FcConfigAppFontAddFile(current, os.fsencode(path)):
                    raise RuntimeError("Fontconfig could not load the bundled font")
                _registered = True
            bundled = True
    except (OSError, RuntimeError) as exc:
        print("Failed to load the emoji font; using system fonts:", exc)

    # Existing Pango font maps cache Fontconfig results across font changes.
    return PangoCairo.FontMap.new(), bundled
