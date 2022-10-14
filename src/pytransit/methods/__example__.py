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

from pytransit.generic_tools import csv, misc, informative_iterator
from pytransit.specific_tools import logging, gui_tools, transit_tools, tnseq_tools, norm_tools, console_tools
from pytransit.globals import gui, cli, root_folder, debugging_enabled
from pytransit.components import samples_area, results_area, parameter_panel, file_display

from pytransit.generic_tools.lazy_dict import LazyDict
from pytransit.specific_tools.transit_tools import wx, basename, HAS_R, FloatVector, DataFrame, StrVector
from pytransit.components.spreadsheet import SpreadSheet


@misc.singleton
class Method:
    name = "Example" # HANDLE_THIS
    identifier  = name
    cli_name    = name.lower()
    menu_name   = f"{name} - Perform {name} analysis"
    description = f"""Perform {name} analysis"""
    
    inputs = LazyDict(
        output_path=None,
        normalization="TTR",
        n_terminus=0.0,
        c_terminus=0.0,
        # HANDLE_THIS
    )
    
    valid_cli_flags = [
        "-n",  # normalization
        "-iN", # n_terminus
        "-iC", # c_terminus
        # HANDLE_THIS
    ]
    usage_string = f"""
        # HANDLE_THIS
        Usage: {console_tools.subcommand_prefix} {cli_name} [Optional Arguments]
        Optional Arguments:
            -n <string>         :=  Normalization method. Default: -n TTR
            -iN <N> :=  Ignore TAs within given percentage (e.g. 5) of N terminus. Default: -iN 0
            -iC <N> :=  Ignore TAs within given percentage (e.g. 5) of C terminus. Default: -iC 0
    """.replace("\n        ", "\n")
    
    @gui.add_wig_area_dropdown_option(name=name)
    def on_wig_option_click():
        print("You clicked a dropdown option")
    
    @gui.add_menu("Method", "himar1", menu_name)
    def on_menu_click(event):
        Method.define_panel(event)
    
    @gui.add_menu("Method", "tn5", menu_name)
    def on_menu_click(event):
        Method.define_panel(event)
    
    def define_panel(self, _):
        from pytransit.components import panel_helpers
        with panel_helpers.NewPanel() as (panel, main_sizer):
            set_instructions(
                method_short_text=self.name,
                method_long_text="",
                method_descr="""
                    HANDLE_THIS
                """.replace("\n                    ","\n"),
                method_specific_instructions="""
                    HANDLE_THIS
                """.replace("\n                    ","\n"),
            )
            self.value_getters = LazyDict()
            # panel_helpers.create_float_getter(panel, main_sizer, label_text="", default_value=0, tooltip_text="")
            # panel_helpers.create_int_getter(panel, main_sizer, label_text="", default_value=0, tooltip_text="")
            # panel_helpers.create_file_input(panel, main_sizer, button_label="", tooltip_text="", popup_title="", default_folder=None, default_file_name="", allowed_extensions='All files (*.*)|*.*')
            # panel_helpers.create_choice_input(panel, main_sizer, label="", options=[], default_option=None, tooltip_text="")
            # panel_helpers.create_text_box_getter(panel, main_sizer, label_text="", default_value="", tooltip_text="", label_size=None, widget_size=None,)
            # panel_helpers.create_check_box_getter(panel, main_sizer, label_text="", default_value=False, tooltip_text="", widget_size=None)
            # @panel_helpers.create_button(panel, main_sizer, label="")
            # def when_button_clicked(event):
            #     print("do stuff")
            
            self.value_getters.n_terminus             = panel_helpers.create_n_terminus_input(panel, main_sizer)
            self.value_getters.c_terminus             = panel_helpers.create_c_terminus_input(panel, main_sizer)
            self.value_getters.normalization          = panel_helpers.create_normalization_input(panel, main_sizer)
            
            panel_helpers.create_run_button(panel, main_sizer, from_gui_function=self.from_gui)
            
    @staticmethod
    def from_gui(frame):
        # 
        # global data
        # 
        # HANDLE_THIS
        gui.is_active # false if using command line
        gui.frame # self.wxobj equivalent
        gui.busy_running_method # Boolean, is true when any .Run() is started but not finished
        gui.annotation_path # string, may need to become a list of strings
        gui.samples # list of Wig objects
        gui.conditions # list of Condition objects
        gui.selected_samples # list of Wig objects
        gui.selected_conditions # list of Condition objects
        gui.selected_condition_names # list of strings
        gui.conditions[0].name # string
        gui.conditions[0].extra_data # dict (currently unused, but would show up as columns in the condition GUI table)
        gui.wigs_in_selected_conditions # list of Wig objects
        gui.combined_wigs # list of CombinedWig objects
        gui.combined_wigs[-1].as_tuple # (numpy.array(sites), numpy.array(counts_by_wig), wig_fingerprints)
        gui.combined_wigs[-1].main_path
        gui.combined_wigs[-1].metadata_path # to get all these it would be [ each.metadata_path for each in gui.combined_wigs ]
        gui.combined_wigs[-1].samples # list of Wig objects
        gui.combined_wigs[-1].samples[0].id # id from the metadata file
        gui.combined_wigs[-1].samples[0].fingerprint # the "File" column from the metadata 
        gui.combined_wigs[-1].samples[0].condition_names # a list of strings
        gui.combined_wigs[-1].samples[0].positions # list of ints
        gui.combined_wigs[-1].samples[0].insertion_counts # list of numbers
        gui.combined_wigs[-1].samples[0].rows # each element is always [position_number, insertion_count]
        gui.combined_wigs[-1].samples[0].column_index # int (column inside combined wig)
        gui.combined_wigs[-1].samples[0].extra_data.count
        gui.combined_wigs[-1].samples[0].extra_data.sum
        gui.combined_wigs[-1].samples[0].extra_data.non_zero_mean
        gui.combined_wigs[-1].samples[0].extra_data.non_zero_median
        gui.combined_wigs[-1].samples[0].extra_data.density
        gui.combined_wigs[-1].samples[0].extra_data.mean
        gui.combined_wigs[-1].samples[0].extra_data.max
        gui.combined_wigs[-1].samples[0].extra_data.skew
        gui.combined_wigs[-1].samples[0].extra_data.kurtosis
        gui.combined_wigs[-1].metadata # CombinedWigMetadata object
        gui.combined_wigs[-1].metadata.path
        gui.combined_wigs[-1].metadata.headers
        gui.combined_wigs[-1].metadata.rows
        gui.combined_wigs[-1].metadata.conditions
        gui.combined_wigs[-1].metadata.condition_names
        gui.combined_wigs[-1].metadata.wig_ids
        gui.combined_wigs[-1].metadata.wig_fingerprints
        gui.combined_wigs[-1].metadata.with_only(condition_names=[], wig_fingerprints=[])
        gui.combined_wigs[-1].metadata.condition_for(wig_fingerprint) # will need to change to "conditions" instead of "condition"
        gui.combined_wigs[-1].metadata.condition_for(wig_id) # will need to change to "conditions" instead of "condition"
        gui.combined_wigs[-1].metadata.id_for(wig_fingerprint)
        gui.combined_wigs[-1].metadata.fingerprints_for(condition_name)
        gui.combined_wigs[-1].rows # equivalent to the CSV rows of .comwig file; a list of lists, can contain numbers and strings
        
        # 
        # get annotation
        # 
        # HANDLE_THIS
        Method.inputs.annotation_path = gui.annotation_path
        
        # 
        # call all GUI getters, puts results into respective Method.inputs key-value
        # 
        for each_key, each_getter in Method.value_getters.items():
            try:
                Method.inputs[each_key] = each_getter()
            except Exception as error:
                logging.error(f'''Failed to get value of "{each_key}" from GUI:\n{error}''')
        
        # 
        # ask for output path(s)
        # 
        Method.inputs.output_path = gui_tools.ask_for_output_file_path(
            default_file_name=f"{Method.cli_name}_output.csv",
            output_extensions='Common output extensions (*.txt,*.csv,*.dat,*.out)|*.txt;*.csv;*.dat;*.out;|\nAll files (*.*)|*.*',
        )
        # if user didn't select an output path
        if not Method.inputs.output_path:
            return None

        return Method

    @staticmethod
    @cli.add_command(cli_name)
    def from_args(args, kwargs):
        console_tools.handle_help_flag(kwargs, Method.usage_string)
        console_tools.handle_unrecognized_flags(Method.valid_cli_flags, kwargs, Method.usage_string)
        console_tools.enforce_number_of_args(args, Method.usage_string, exactly=4)

        # save the data
        Method.inputs.update(dict(
            output_path=args[0],
            normalization=kwargs.get("n", Method.inputs.normalization),
            n_terminus=float(kwargs.get("iN", Method.inputs.n_terminus)),
            c_terminus=float(kwargs.get("iC", Method.inputs.c_terminus)),
            # HANDLE_THIS
        ))
        
        Method.Run()
        
    def Run(self):
        from pytransit.specific_tools import stat_tools
        logging.log(f"Starting {Method.identifier} analysis")
        start_time = time.time()
        
        # 
        # process data
        # 
        if True:
            rows, summary_info = stat_tools.{analysis_name}(**self.inputs) # HANDLE_THIS
        
        # 
        # write output
        # 
        if True:
            logging.log(f"Adding File: {self.inputs.output_path}")
            # 
            # write to file
            # 
            transit_tools.write_result(
                path=self.inputs.output_path, # path=None means write to STDOUT
                file_kind=Method.identifier,
                rows=rows,
                column_names=[
                    # HANDLE_THIS
                ],
                extra_info=dict(
                    stats=dict(summary_info), # HANDLE_THIS
                    parameters=self.inputs,
                ),
            )
            logging.log(f"Finished {Method.identifier} analysis in {time.time() - start_time:0.1f}sec")
        results_area.add(self.inputs.output_path)

@transit_tools.ResultsFile
class ResultFileType1:
    @staticmethod
    def can_load(path):
        return transit_tools.file_starts_with(path, '#'+Method.identifier)
    
    def __init__(self, path=None):
        self.wxobj = None
        self.path  = path
        self.values_for_result_table = LazyDict(
            name=basename(self.path),
            type=Method.identifier,
            path=self.path,
            # anything with __ is not shown in the table
            __dropdown_options=LazyDict({
                "Display Table": lambda *args: SpreadSheet(
                    title=Method.identifier,
                    heading=self.comments_string or misc.human_readable_data(self.extra_data),
                    column_names=self.column_names,
                    rows=self.rows,
                    sort_by=[
                        # HANDLE_THIS
                    ],
                ).Show(),
            })
        )
        
        # 
        # read in data
        # 
        self.column_names, self.rows, self.extra_data, self.comments_string = tnseq_tools.read_results_file(self.path)
        self.values_for_result_table.update(self.extra_data.get("parameters", {}))
        
        # 
        # get summary stats
        #
        self.values_for_result_table.update({
            # HANDLE_THIS (additional summary_info for results table)
            # examples:
                # f"Gene Count": len(self.rows),
                # f"Adj P Value < {Method.significance_threshold}": len([
                #     1 for each in self.rows
                #         if each.get("Adj P Value", 0) < Method.significance_threshold 
                # ]),
        })
    
    def __str__(self):
        return f"""
            File for {Method.identifier}
                path: {self.path}
                column_names: {self.column_names}
        """.replace('\n            ','\n').strip()

