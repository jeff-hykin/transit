import sys

from pytransit.transit_tools import HAS_WX, wx, GenBitmapTextButton, pub

import traceback
import datetime
import pytransit.transit_tools as transit_tools
from pytransit.components.menu import convert_menu_item
from pytransit.components.icon import InfoIcon
from pytransit.transit_tools import InvalidArgumentException


class ConvertGUI:
    def __init__(self):
        self.wxobj = None
        self.menuitem = None
        self.LABELSIZE = (100, -1)
        self.WIDGETSIZE = (100, -1)

    def defineMenuItem(self, wxobj, label):
        # TODO: write docstring

        self.wxobj = wxobj

        self.menuitem = wx.MenuItem(
            convert_menu_item,
            wx.ID_ANY,
            label,
            wx.EmptyString,
            wx.ITEM_NORMAL,
        )


class ConvertMethod:
    """
    Basic class for convert methods.
    """

    def __init__(
        self,
        short_name,
        long_name,
        description,
        label,
        annotation_path,
        output,
        wxobj=None,
    ):
        self.short_name = short_name
        self.long_name = long_name
        self.description = description
        self.label = label
        self.output = output
        self.annotation_path = annotation_path

        self.WX_VERSION = WX_VERSION
        self.wxobj = wxobj

    @classmethod
    def from_gui(self, wxobj):
        # TODO: write docstring
        raise NotImplementedError

    @classmethod
    def fromargs(self, rawargs):
        # TODO: write docstring
        raise NotImplementedError

    @classmethod
    def fromconsole(self):
        # TODO: write docstring
        try:
            return self.fromargs(sys.argv[3:])
        except InvalidArgumentException as e:
            print("Error: %s" % str(e))
            print(self.usage_string())
        except IndexError as e:
            print("Error: %s" % str(e))
            print(self.usage_string())
        except TypeError as e:
            print("Error: %s" % str(e))
            traceback.print_exc()
            print(self.usage_string())
        except ValueError as e:
            print("Error: %s" % str(e))
            traceback.print_exc()
            print(self.usage_string())
        except Exception as e:
            print("Error: %s" % str(e))
            traceback.print_exc()
            print(self.usage_string())
        sys.exit()

    @classmethod
    def usage_string(self):
        # TODO: write docstring
        raise NotImplementedError

    def Run(self):
        # TODO write docstring
        raise NotImplementedError

    def finish(self):
        # TODO: write docstring
        if self.wxobj:
            wx.CallAfter(pub.sendMessage, "finish", msg=self.short_name.lower())

    def console_message(self, text):
        # TODO: write docstring
        sys.stdout.write("[%s] %s\n" % (self.short_name, text))

    def console_message_inplace(self, text):
        # TODO: write docstring
        sys.stdout.write("[%s] %s   \r" % (self.short_name, text))
        sys.stdout.flush()

    def transit_message_inplace(self, text):
        # TODO: write docstring
        self.console_message_inplace(text)

    def transit_error(self, text):
        transit_tools.log(text)
        if self.wxobj:
            transit_tools.show_error_dialog(text)

    def transit_warning(self, text):
        transit_tools.log(text)
        if self.wxobj:
            transit_tools.ShowWarning(text)

class TransitConvert:
    def __init__(
        self, sn, ln, desc, lab, method_class=ConvertMethod, gui_class=ConvertGUI
    ):
        self.short_name  = sn
        self.long_name   = ln
        self.description = desc
        self.short_desc  = self.long_name
        self.long_desc   = desc
        self.full_name   = f"[{self.short_name}]  -  {self.short_desc}"
        self.label       = lab
        self.method      = method_class
        self.gui         = gui_class()
        self.transposons_text = ""

    def __str__(self):
        return f"""
            Convert Method:
                Short Name:  {self.short_name}
                Long Name:   {self.long_name}
                Description: {self.description}
                Method:      {self.method}
                GUI:         {self.gui}
        """.replace('\n            ','\n').strip()