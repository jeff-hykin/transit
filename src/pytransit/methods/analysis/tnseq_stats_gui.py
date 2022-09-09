import sys
import os
import time
import ntpath
import math
import random
import datetime
import heapq
import collections

import numpy
from pytransit.basics.lazy_dict import LazyDict

from pytransit.universal_data import universal
from pytransit.components.parameter_panel import panel as parameter_panel
from pytransit.components.parameter_panel import progress_update
from pytransit.components.panel_helpers import make_panel, create_run_button, create_button, create_normalization_input
from pytransit.components.spreadsheet import SpreadSheet
import pytransit.tools.gui_tools as gui_tools
import pytransit.tools.console_tools as console_tools
import pytransit.tools.transit_tools as transit_tools
import pytransit.tools.tnseq_tools as tnseq_tools
import pytransit.tools.norm_tools as norm_tools
import pytransit.tools.stat_tools as stat_tools
import pytransit.basics.csv as csv
import pytransit.components.results_area as results_area

command_name = sys.argv[0]

class Analysis:
    identifier  = "#tnseq_stats_gui"
    short_name  = "tnseq_stats_gui"
    long_name   = "tnseq_stats_gui"
    short_desc  = "Analyze statistics of TnSeq datasets"
    long_desc   = """Analyze statistics of TnSeq datasets in combined_wig file"""
    transposons = [ "himar1" ]
    
    inputs = LazyDict(
        combined_wig=None,
        normalization=None,
        output_path=None,
    )
    
    valid_cli_flags = [
        "-n", # normalization flag
        "-o", # output filename (optional)
        "-c", # indicates whether input is list of wig files (comma- or space-separated?), or a combined_wig file
    ]
    usage_string = f"""usage: python3 %s tnseq_stats <file.wig>+ [-o <output_file>]\n       python %s tnseq_stats -c <combined_wig> [-o <output_file>]""" % (sys.argv[0],sys.argv[0])
    
    
    wxobj = None
    panel = None
    
    def __init__(self, *args, **kwargs):
        Analysis.instance = self
        self.full_name        = f"[{self.short_name}]  -  {self.short_desc}"
        self.transposons_text = transit_tools.get_transposons_text(self.transposons)
        self.filetypes        = [File]
        self.method           = Analysis # backwards compat
        self.gui              = self     # backwards compat
    
    def __str__(self):
        return f"""
            Analysis Method:
                Short Name:  {self.short_name}
                Long Name:   {self.long_name}
                Short Desc:  {self.short_desc}
                Long Desc:   {self.long_desc}
                GUI:         {self.gui}
        """.replace('\n            ','\n').strip()
    
    def __repr__(self):
        return f"{self.inputs}"

    def define_panel(self, _):
        from pytransit.tools.transit_tools import wx
        self.panel = make_panel()

        # only need Norm selection and Run button        
        self.value_getters = LazyDict()
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.value_getters.normalization = create_normalization_input(self.panel, main_sizer,default="nonorm")
        create_run_button(self.panel, main_sizer)

        parameter_panel.set_panel(self.panel)
        self.panel.SetSizer(main_sizer)
        self.panel.Layout()
        main_sizer.Fit(self.panel)

    @classmethod
    def from_gui(cls, frame):
        with gui_tools.nice_error_log:
            # 
            # get wig files
            # 
            combined_wig = universal.session_data.combined_wigs[0]
            Analysis.inputs.combined_wig = combined_wig.main_path
            
            # 
            # get annotation
            # 
            ###Analysis.inputs.annotation_path = universal.session_data.annotation # not needed for tnseq_stats
            # FIXME: enable this once I get a valid annotation file example
            # if not transit_tools.validate_annotation(Analysis.inputs.annotation):
            #     return None
            
            # 
            # setup custom inputs
            # 
            for each_key, each_getter in Analysis.instance.value_getters.items():
                try:
                    Analysis.inputs[each_key] = each_getter()
                except Exception as error:
                    raise Exception(f'''Failed to get value of "{each_key}" from GUI:\n{error}''')
            ###transit_tools.log("included_conditions", Analysis.inputs.included_conditions)

            # 
            # save result files
            # 
            Analysis.inputs.output_path = gui_tools.ask_for_output_file_path(
                default_file_name="tnseq_stats.dat",
                output_extensions='Common output extensions (*.txt,*.dat,*.out)|*.txt;*.dat;*.out;|\nAll files (*.*)|*.*',
            )
            if not Analysis.inputs.output_path:
                return None

            return Analysis.instance

    @classmethod
    def from_args(cls, args, kwargs):
        console_tools.handle_help_flag(kwargs, cls.usage_string)
        console_tools.handle_unrecognized_flags(cls.valid_cli_flags, kwargs, cls.usage_string)

        normalization = kwargs.get("n", "nonorm") 
        output_path = kwargs.get("o", None)

        # save all the data
        Analysis.inputs.update(dict(
            combined_wig=combined_wig, ### what if user gives a list of wig files instead of a combined_wig?
            normalization=normalization,
            output_path=output_path,
        ))
        
        return Analysis.instance
        
    def Run(self):
        with gui_tools.nice_error_log:
            transit_tools.log("Starting tnseq_stats analysis")
            start_time = time.time()

            # if you want to see which samples were selected...
            #from pytransit.components.samples_area import sample_table
            #datasets_selected = [ each_row["path"] for each_row in sample_table.selected_rows ]
            #for x in datasets_selected: print(str(x))

            # 
            # get data
            # 
            transit_tools.log("Getting Data")
            if True:
                sites, data, filenames_in_comb_wig = tnseq_tools.read_combined_wig(self.inputs.combined_wig)
                
                transit_tools.log(f"Normalizing using: {self.inputs.normalization}")
                data, factors = norm_tools.normalize_data(data, self.inputs.normalization)
                
            # 
            # process data
            # 

            transit_tools.log("processing data")
            results = self.calc_tnseq_stats(data,filenames_in_comb_wig)

            # 
            # write output
            # 
            # note: first comment line is filetype, last comment line is column headers

            transit_tools.log(f"Adding File: {self.inputs.output_path}")
            results_area.add(self.inputs.output_path)

            file = sys.stdout # print to console if not output file defined
            if self.inputs.output_path != None:
               file = open(self.inputs.output_path, "w")
            file.write("%s\n" % self.identifier)
            file.write("#normalization: %s\n" % self.inputs.normalization)
            file.write("#dataset\tdensity\tmean_ct\tNZmean\tNZmedian\tmax_ct\ttotal_cts\tskewness\tkurtosis\tpickands_tail_index\n")

            for vals in results:
              file.write("\t".join([str(x) for x in vals]) + "\n")

            if self.inputs.output_path != None: file.close()
            transit_tools.log("Finished TnseqStats")
            transit_tools.log("Time: %0.1fs\n" % (time.time() - start_time))

    def pickands_tail_index(self, vals):
        srt = sorted(vals, reverse=True)
        PTIs = []
        for M in range(10, 100):
            PTI = numpy.log(
                (srt[M] - srt[2 * M]) / float(srt[2 * M] - srt[4 * M])
            ) / numpy.log(2.0)
            PTIs.append(PTI)
        return numpy.median(PTIs)

    # data=numpy array of (normalized) insertion counts at TA sites for multiple samples; sample_names=.wig filenames
    def calc_tnseq_stats(self,data,sample_names): 
      results = []
      for i in range(data.shape[0]):
          (
              density,
              meanrd,
              nzmeanrd,
              nzmedianrd,
              maxrd,
              totalrd,
              skew,
              kurtosis,
          ) = tnseq_tools.get_data_stats(data[i, :])
          nzmedianrd = int(nzmedianrd) if numpy.isnan(nzmedianrd) == False else 0
          pti = self.pickands_tail_index(data[i, :])
          vals = [
              sample_names[i],
              "%0.3f" % density,
              "%0.1f" % meanrd,
              "%0.1f" % nzmeanrd,
              "%d" % nzmedianrd,
              maxrd,
              int(totalrd),
              "%0.1f" % skew,
              "%0.1f" % kurtosis,
              "%0.3f" % pti
          ]
          results.append(vals)
      return results


@transit_tools.ResultsFile
class File(Analysis):
    @staticmethod
    def can_load(path):
        with open(path) as in_file:
            for line in in_file:
                if line.startswith("#"):
                    if line.startswith(Analysis.identifier):
                        return True
                else:
                    return False
        return False
    
    def __init__(self, path=None):
        self.wxobj = None
        self.path  = path
        self.values_for_result_table = LazyDict(
            name=transit_tools.basename(self.path),
            type=Analysis.identifier,
            path=self.path,
            # anything with __ is not shown in the table
            __dropdown_options=LazyDict({
                "Display Table": lambda *args: SpreadSheet(title="tnseq_stats",heading="",column_names=self.column_names,rows=self.rows).Show(),
            })
        )
        
        # 
        # get column names
        # 
        comments, headers, rows = csv.read(self.path, seperator="\t", skip_empty_lines=True, comment_symbol="#")
        if len(comments) == 0:
            raise Exception(f'''No comments in file, and I expected the last comment to be the column names, while to load tnseq_stats file "{self.path}"''')
        self.column_names = comments[-1].split("\t")
        
        # 
        # get rows
        #
        self.rows = []
        for each_row in rows:
            row = {}
            for each_column_name, each_cell in zip(self.column_names, each_row):
               row[each_column_name] = each_cell
            self.rows.append(row)
        
    
    def __str__(self):
        return f"""
            File for {self.short_name}
                path: {self.path}
                column_names: {self.column_names}
        """.replace('\n            ','\n').strip()
    
    
Method = GUI = Analysis
Analysis() # make sure there's one instance