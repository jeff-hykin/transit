import traceback
from typing import NamedTuple

from pytransit.transit_tools import wx



window = None
bit_map = None

def rgba(*args):
    return tuple(args)

def bind_to(wxPythonObj, event):
    """
        Usage:
            @bind_to(gui_object, wx.EVENT_THING)
            def callback(event):
                pass
        
    """
    def wrapper2(function_to_attach):
        wxPythonObj.Bind(event, function_to_attach)
        def wrapper1(*args, **kwargs):
            try:
               return function_to_attach(*args, **kwargs)
            except Exception as error:
                handle_error(error)
        return wrapper1
    return wrapper2

def handle_error(error_obj):
    """
        Summary:
            logs error message in bottom corner of GUI
            prints it to console
            and avoids crashing the whole runtime
        Usage:
            try:
                pass
            except Exception as error:
                handle_error
    """
    traceback.print_exc()
    if window and hasattr(window, "statusBar") and hasattr(window.statusBar, "SetStatusText"):
        window.statusBar.SetStatusText("Error: "+str(error_obj.args))

def handle_traceback(traceback_obj):
    import traceback
    print(''.join(traceback.format_tb(traceback_obj)))
    if window and hasattr(window, "statusBar") and hasattr(window.statusBar, "SetStatusText"):
        window.statusBar.SetStatusText("Error: "+str(error.args))

def show_message(MSG=""):
    # TODO: Write docstring
    wx.MessageBox(MSG, "Info", wx.OK | wx.ICON_INFORMATION)


def ask_for_files(message):
    file_dialog = wx.FileDialog(
        window,
        message=message,
        defaultDir=window.workdir,
        defaultFile="",
        style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR,
    )
    output = None
    if file_dialog.ShowModal() == wx.ID_OK:
        output = list(file_dialog.GetPaths())
    file_dialog.Destroy()
    return output


class color(NamedTuple):
    green = rgba(187, 237, 181, 255)

class NiceErrorLog(object):
    """
        Example:
            with nice_error_log:
                print("stuff")
                raise Exception("example error")
                
                # ((error magically gets logged and caught))
    """
    def __init__(*args, **kwargs):
        pass
    
    def __enter__(self):
        return window
    
    def __exit__(self, _, error, traceback_obj):
        if error is not None:
            print(''.join(traceback.format_tb(traceback_obj)))
            if window:
                window.statusBar.SetStatusText("Error: "+str(error.args))

nice_error_log = NiceErrorLog()