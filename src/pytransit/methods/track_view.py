import sys
import os
import time
import ntpath
import math
import random
import datetime
import collections
import heapq

import numpy

from pytransit.specific_tools import logging, gui_tools, transit_tools, tnseq_tools, norm_tools, console_tools
from pytransit.generic_tools.lazy_dict import LazyDict
import pytransit.generic_tools.csv as csv
import pytransit.generic_tools.misc as misc
from pytransit.specific_tools.transit_tools import wx, basename, HAS_R, FloatVector, DataFrame, StrVector, EOL
from pytransit.globals import gui, cli, root_folder, debugging_enabled
from pytransit.components import samples_area, file_display, results_area, parameter_panel
from pytransit.components.spreadsheet import SpreadSheet

@misc.singleton
class Method:
    name = "Track View"
    
    # TODO: confirm menu option not needed
    # @gui.add_menu("Preprocessing", name)
    # def on_menu_click(event):
    #     pass
    
    # 
    # Track View
    # 
    @samples_area.create_sample_area_button(name=name, size=(120, -1))
    @staticmethod
    def click_show_track_view(event):
        with gui_tools.nice_error_log:
            import pytransit.components.trash as trash
            annotation_path = gui.annotation_path
            wig_ids = [ each_sample.id for each_sample in gui.selected_samples ]

            if wig_ids and annotation_path:
                if debugging_enabled:
                    logging.log("Visualizing counts for: %s" % ", ".join(wig_ids))
                view_window = trash.TrashFrame(gui.frame, wig_ids, annotation_path, gene="")
                view_window.Show()
            elif not wig_ids:
                # NOTE: was a popup
                logging.error("Error: No samples selected.")
            else:
                # NOTE: was a popup
                logging.error("Error: No annotation file selected.")