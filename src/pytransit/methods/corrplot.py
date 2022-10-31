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
from pytransit.specific_tools.transit_tools import wx, r, basename, HAS_R, FloatVector, DataFrame, StrVector, globalenv
from pytransit.components.spreadsheet import SpreadSheet

@misc.singleton
class Method:
    name = "Corrplot"
    identifier  = name
    cli_name    = name.lower()
    menu_name   = f"{name} - Make correlation plot"
    description = f"""Make correlation plot"""
    
    transposons = [ "himar1" ] # not sure if this is right -- Jeff
    
    inputs = LazyDict(
        combined_wig=None,
        annotation_path=None,
        output_path=None,
        avg_by_conditions=False,
        normalization="TTR", #TRI hard-coded for now
    )
    
    valid_cli_flags = [ "avg_by_conditions" ]
    #TRI - could add a flag for Adj P Value cutoff (or top n most signif genes)

    # TODO: TRI - should drop anova and zinb defaults, and instead take combined_wig or gene_means file (from export)
    #usage_string = """usage: {console_tools.subcommand_prefix} corrplot <gene_means> <output.png> [-anova|-zinb]""""
    usage_string = f"""usage: {console_tools.subcommand_prefix} {cli_name} <combined_wig> <annotation_file> <output.png> [-avg_by_conditions <metadata_file>]"""
    
    # 
    # CLI method
    # 
    @staticmethod
    @cli.add_command(cli_name)
    def from_args(args, kwargs):
        console_tools.handle_help_flag(kwargs, Method.usage_string)
        console_tools.handle_unrecognized_flags(Method.valid_cli_flags, kwargs, Method.usage_string)
        console_tools.enforce_number_of_args(args, Method.usage_string, exactly=4)
                
        # map data to the core function
        Method.output(
            combined_wig=tnseq_tools.CombinedWig(
                main_path=args[0],
                metadata_path=args[1],
                annotation_path=args[2],
            ),
            normalization=kwargs["n"],
            n_terminus=kwargs["iN"],
            c_terminus=kwargs["iC"],
            avg_by_conditions="avg_by_conditions" in kwargs, # bool
            output_path=args[3],
            disable_logging=False,
        )
    
    # 
    # Panel method
    # 
    @gui.add_menu("Pre-Processing", menu_name)
    def on_menu_click(event):
        Method.define_panel(event)
    
    def define_panel(self, _):
        from pytransit.components import panel_helpers
        with panel_helpers.NewPanel() as (panel, main_sizer):
            parameter_panel.set_instructions(
                title_text= self.name,
                sub_text= "",
                method_specific_instructions="""
                    A useful tool when evaluating the quality of a collection of TnSeq datasets is to make a correlation plot of the mean insertion counts (averaged at the gene-level) among samples.

                    1. Ensure the correct annotation file has been loaded in 
                    
                    2. Select whether you would like to calculate the means across replicates within a condition

                    3. Click Run
                """.replace("\n                    ","\n")
            )


            self.value_getters = LazyDict()
            self.value_getters.avg_by_conditions = panel_helpers.create_check_box_getter(panel, main_sizer, label_text="average counts by condition", default_value=False, tooltip_text="correlations among conditions (where counts are averaged among replicates of each condition) versus all individual samples", widget_size=None)
            self.value_getters.normalization     = panel_helpers.create_normalization_input(panel, main_sizer)

            panel_helpers.create_run_button(panel, main_sizer, from_gui_function=self.from_gui)
            
    @staticmethod
    def from_gui(frame):
        arguments = LazyDict()
        
        # 
        # get global data
        # 
        arguments.combined_wig = gui.combined_wigs[-1] #TRI what if not defined? fail gracefully?
        
        # 
        # call all GUI getters, puts results into respective Method.defaults key-value
        # 
        for each_key, each_getter in Method.value_getters.items():
            try:
                arguments[each_key] = each_getter()
            except Exception as error:
                logging.error(f'''Failed to get value of "{each_key}" from GUI:\n{error}''')
        
        # 
        # ask for output path(s)
        # 
        arguments.output_path = gui_tools.ask_for_output_file_path(
            default_file_name=f"corrplot.png",
            output_extensions='PNG file (*.png)|*.png;|\nAll files (*.*)|*.*',
        )
        
        # if user didn't select an output path
        if not arguments.output_path:
            return None
        
        # run the core function directly
        Method.output(**arguments)
    
    corrplot_r_function = None    
    @staticmethod
    def output(*, combined_wig_path=None, metadata_path=None, annotation_path=None, combined_wig=None, normalization=None, avg_by_conditions=None, output_path=None, n_terminus=None, c_terminus=None, disable_logging=False):
        # Defaults (even if argument directly provided as None)
        normalization     = normalization     if normalization     is not None else "TTR"
        avg_by_conditions = avg_by_conditions if avg_by_conditions is not None else False
        output_path       = output_path       if output_path       is not None else None
        n_terminus        = n_terminus        if n_terminus        is not None else 0.0
        c_terminus        = c_terminus        if c_terminus        is not None else 0.0
        
        if combined_wig == None:
            combined_wig = tnseq_tools.CombinedWig(main_path=combined_wig_path,metadata_path=metadata_path, annotation_path=annotation_path)
        
        from pytransit.methods.gene_means import Method as GeneMeansMethod
        with transit_tools.TimerAndOutputs(method_name=Method.identifier, output_paths=[output_path], disable=disable_logging,):
            import seaborn as sns
            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd

            _, (means, genes, headers) = GeneMeansMethod.calculate(combined_wig, normalization=normalization, avg_by_conditions=avg_by_conditions, n_terminus=n_terminus, c_terminus=c_terminus)
            
            position_hash = {}
            for i, col in enumerate(headers):
                position_hash[col] = FloatVector([x[i] for x in means])
            df = pd.DataFrame.from_dict(position_hash, orient="columns")  

            logging.log("Creating the Correlation Plot")
            corr = df[headers].corr()
            mask = np.triu(np.ones_like(corr, dtype=bool))
            #f, ax = plt.subplots(figsize=(11, 9))
            plt.figure()
            sns.heatmap(corr, mask=mask, cmap=sns.color_palette("bwr", as_cmap=True),  square=True, linewidths=.5, cbar_kws={"shrink": .5})
            if avg_by_conditions == False:
                plt.title("Correlations of Genes in Samples")
            else:
                plt.title("Correlations of Genes in Conditions")
            plt.savefig(output_path, bbox_inches='tight')