from pytransit.components.parameter_panel import panel, progress_update
import sys
import os
import time

from pytransit.specific_tools import logging, gui_tools, transit_tools, tnseq_tools, norm_tools, console_tools
from pytransit.generic_tools.lazy_dict import LazyDict
from pytransit.generic_tools import misc, informative_iterator
from pytransit.globals import gui, cli, root_folder, debugging_enabled

@misc.singleton
class Method:
    name = "normalize"
    description = "Method for normalizing datasets and outputting into CombinedWig file."
    usage_string = f"""
        {console_tools.subcommand_prefix} norm <comma-separated .wig files> <annotation .prot_table or GFF3> <output file> [Optional Arguments]
    
            Optional Arguments:
            -n <string>     :=  Normalization method. Default: -n TTR
    """.replace("\n        ","\n")
    
    options = [
        "TTR",
        "nzmean",
        "totreads",
        "zinfnb",
        "quantile",
        "betageom",
        "nonorm",
    ]
    
    
    # 
    # newer method
    # 
    menu_prefix = ("Pre-Processing", "Normalize Using")
    @gui.add_menu(*menu_prefix, "Trimmed Total Reads")
    def menu_options(*args): Method.gui_normalize(kind="TTR")
    
    @gui.add_menu(*menu_prefix, "Non-Zero Mean")
    def menu_options(*args): Method.gui_normalize(kind="nzmean")
    
    @gui.add_menu(*menu_prefix, "Total Reads")
    def menu_options(*args): Method.gui_normalize(kind="totreads")
    
    @gui.add_menu(*menu_prefix, "Beta-Geometric Correction (BCG)")
    def menu_options(*args): Method.gui_normalize(kind="betageom")
    
    @gui.add_menu(*menu_prefix, "Zero-Inflated Negative Binomial (ZINFNB)")
    def menu_options(*args): Method.gui_normalize(kind="zinfnb")
    
    @gui.add_menu(*menu_prefix, "Quantile")
    def menu_options(*args): Method.gui_normalize(kind="quantile")
    
    # a helper for all the methods above
    def gui_normalize(self, kind):
        # FIXME: ask the user for the combined wig instead of operating on the one that (is presumably) loaded
        return Method.run_normalize(
            combined_wig=gui.combined_wigs[-1],
            output_path=gui_tools.ask_for_output_file_path(
                default_file_name=f"{Method.name}_output.csv".lower(),
                output_extensions='Common output extensions (*.csv,*.dat,*.txt,*.out)|*.csv;*.dat;*.txt;*.out;|\nAll files (*.*)|*.*',
            ),
            normalization=kind,
        )
    
    @cli.add_command("normalize")
    @staticmethod
    def from_args(args, kwargs):
        is_combined_wig = "c" in kwargs
        if is_combined_wig:
            console_tools.enforce_number_of_args(args, Method.usage_string, at_least=1)
            infile_path = kwargs.get("c")
            combined_wig = tnseq_tools.CombinedWig(main_path=infile_path)
            output_path = args[0]  # if no arg give, could print to screen
        else:
            console_tools.enforce_number_of_args(args, Method.usage_string, at_least=2)
            combined_wig = False
            infile_path = args[0]  # only 1 input wig file
            output_path = args[1]  # if no arg give, could print to screen
        
        Method.run_normalize(
            combined_wig=combined_wig,
            infile_path=infile_path,
            output_path=output_path,
            normalization=kwargs.get("n", "TTR"),
        )

    @staticmethod
    def run_normalize(combined_wig, infile_path, output_path, normalization):
        with gui_tools.nice_error_log:
            logging.log("Starting Normalization")
            start_time = time.time()

            # 
            # combined_wig
            # 
            if combined_wig:
                from pytransit.methods.combined_wig import Method as combined_wig_method
                
                (sites, counts_by_wig, wig_fingerprints) = combined_wig.as_tuple
                logging.log(f"normalization={normalization}, counts_by_wig.shape={counts_by_wig.shape}")
                (counts_by_wig, factors) = norm_tools.normalize_data(counts_by_wig, normalization)
                
                transit_tools.write_result(
                    path=output_path, # path=None means write to STDOUT
                    file_kind=combined_wig_method.identifier,
                    column_names=[
                        "TA Site Position",
                        *combined_wig.wig_fingerprints,
                    ],
                    rows=[
                        [
                            each_site,
                            *[
                                "%0.1f" % x for x in list(counts_by_wig[..., ta_site_index])
                            ]
                        ]
                            for ta_site_index, each_site in enumerate(sites)
                    ],
                    extra_info={
                        **combined_wig.extra_data,
                        **dict(
                            time=(time.time() - start_time),
                            normalization=normalization,
                            original_path=infile_path,
                        ),
                    },
                )
            # 
            # regular wig
            # 
            else:
                # 
                # parse "variableStep chrom=" if it exists
                # 
                refernce_genome = ""
                other_data = []
                with open(infile_path) as file:
                    line = file.readline()
                    # skip all the comments
                    while line.startswith("#"):
                        line = file.readline()
                    # get the genome
                    if line.startswith("variableStep"):
                        splits = line.strip().split(" ")
                        for each in splits:
                            assignment_maybe = each.split("=")
                            if len(assignment_maybe) == 2:
                                name, value = each.split("=")
                                if name == "chrom":
                                    refernce_genome = value
                            else:
                                other_data.append(each)
                # 
                # compute
                # 
                (data, sites) = tnseq_tools.CombinedWig.gather_wig_data([ infile_path ])
                logging.log(f"normalization={normalization}, counts_by_wig.shape={data.shape}")
                (data, factors) = norm_tools.normalize_data(data, normalization)
                
                # 
                # write
                # 
                transit_tools.write_result(
                    path=output_path, # path=None means write to STDOUT
                    file_kind="Wig",
                    column_names=[
                        "TA Site Position",
                        "Insertion Count",
                    ],
                    rows=[
                        (each_site, int(data[0, site_index]))
                            for site_index, each_site in enumerate(sites)
                    ],
                    extra_info=dict(
                        time=(time.time() - start_time),
                        normalization=normalization,
                        original_path=infile_path,
                        other_data=other_data,
                    ),
                )
            gui.add_result(output_path)
            logging.log("Finished Normalization")

    
    # 
    # older method
    # 
    # TODO: probably remove this
    @cli.add_command("export", "norm")
    @staticmethod
    def from_export(args, kwargs):
        console_tools.enforce_number_of_args(args, Method.usage_string, at_least=3)
        Method.run_norm(
            ctrldata=args[0].split(","),
            annotation_path=args[1],
            output_path=args[2],
            normalization=kwargs.get("n", "TTR"),
        )
    
    @staticmethod
    def run_norm(ctrldata, annotation_path, output_path, normalization):
        logging.log("Starting Normalization")
        transit_tools.convert_to_combined_wig(
            ctrldata,
            annotation_path,
            output_path,
            normchoice=normalization,
        )
        logging.log("Finished Normalization")