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
import pytransit.components.file_display as file_display
import pytransit.components.results_area as results_area
from pytransit.specific_tools.transit_tools import wx, basename, HAS_R, FloatVector, DataFrame, StrVector
from pytransit.globals import gui, cli, root_folder, debugging_enabled
from pytransit.components.parameter_panel import progress_update, set_instructions
from pytransit.components.spreadsheet import SpreadSheet
from pytransit.generic_tools import misc, csv, informative_iterator

@misc.singleton
class Method:
    name = "Anova"
    identifier  = name
    cli_name    = name.lower()
    menu_name   = f"{name} - analysis of variance"
    description = """Perform Anova analysis"""
    
    transposons = ["himar1", "tn5"]
    significance_threshold = 0.05
    
    inputs = LazyDict(
        combined_wig=None,
        metadata=None,
        annotation=None,
        normalization="TTR",
        output_path=None,
        
        excluded_conditions=[],
        included_conditions=[],
        n_terminus=0.0,
        c_terminus=0.0,
        pseudocount=5,
        winz=False,
        refs=[],
        alpha=1000,
    )
    
    valid_cli_flags = [
        "-n",
        "--include-conditions",
        "--exclude-conditions",
        "--ref",
        "-iN",
        "-iC",
        "-PC",
        "-alpha",
        "-winz",
    ]
    usage_string = f"""
        Usage: {console_tools.subcommand_prefix} anova <combined wig file> <samples_metadata file> <annotation .prot_table> <output file> [Optional Arguments]
        Optional Arguments:
            -n <string>         :=  Normalization method. Default: -n TTR
            --include-conditions <cond1,...> := Comma-separated list of conditions to use for analysis (Default: all)
            --exclude-conditions <cond1,...> := Comma-separated list of conditions to exclude (Default: none)
            --ref <cond> := which condition(s) to use as a reference for calculating LFCs (comma-separated if multiple conditions)
            -iN <N> :=  Ignore TAs within given percentage (e.g. 5) of N terminus. Default: -iN 0
            -iC <N> :=  Ignore TAs within given percentage (e.g. 5) of C terminus. Default: -iC 0
            -PC <N> := pseudocounts to use for calculating LFCs. Default: -PC 5
            -alpha <N> := value added to mse in F-test for moderated anova (makes genes with low counts less significant). Default: -alpha 1000
            -winz   := winsorize insertion counts for each gene in each condition (replace max cnt with 2nd highest; helps mitigate effect of outliers)
    """.replace("\n        ", "\n")
    
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
                method_short_text= self.name,
                method_long_text= "",
                method_descr="""
                    The Anova (analysis of variance) method is used to determine which genes exhibit statistically significant 
                    variability of insertion counts across multiple conditions. Unlike other methods which take a comma-separated list of wig 
                    files as input, the method takes a combined_wig file (which combined multiple datasets in one file) and a samples_metadata file 
                    (which describes which samples/replicates belong to which experimental conditions).
                """.replace("\n                    "," "),
                method_specific_instructions="""
                    1. Ensure you have the annotation file ("prot table") that corresponds to the datasets to be analyzed.
                    
                    2. Select reference condition for the analysis
                    
                    3. [Optional] Add in comma-seperated values of conditions to include and comma-seperated values of condtions to exclude. If these values are not provided, all conditions in the Condtion Panel will be included
                    
                    4. Adjust other parameters to your liking
                    
                    5. Click Run
                """.replace("\n                    ","\n")
            )
            # 
            # parameter inputs
            # 
            # --include-conditions <cond1,...> := Comma-separated list of conditions to use for analysis (Default: all)
            # --exclude-conditions <cond1,...> := Comma-separated list of conditions to exclude (Default: none)
            # --ref <cond> := which condition(s) to use as a reference for calculating lfc_s (comma-separated if multiple conditions)
            # -iN <N> :=  Ignore TAs within given percentage (e.g. 5) of N terminus. Default: -iN 0
            # -iC <N> :=  Ignore TAs within given percentage (e.g. 5) of C terminus. Default: -iC 0
            # -PC <N> := pseudocounts to use for calculating LFC. Default: -PC 5
            # -winz   := winsorize insertion counts for each gene in each condition (replace max cnt with 2nd highest; helps mitigate effect of outliers)
            self.value_getters = LazyDict(
                included_conditions= panel_helpers.create_selected_condition_names_input(panel, main_sizer),
                excluded_conditions= (lambda *args: []), # never needed, but exists to comply with CLI interface
                reference_condition= panel_helpers.create_reference_condition_input(panel, main_sizer),
                n_terminus=          panel_helpers.create_n_terminus_input(panel, main_sizer),
                c_terminus=          panel_helpers.create_c_terminus_input(panel, main_sizer),
                normalization=       panel_helpers.create_normalization_input(panel, main_sizer),
                pseudocount=         panel_helpers.create_pseudocount_input(panel, main_sizer),
                alpha=               panel_helpers.create_alpha_input(panel, main_sizer),
                winz=                panel_helpers.create_winsorize_input(panel, main_sizer),
                refs=                (lambda *args: [] if self.value_getters.reference_condition() == "[None]" else [ self.value_getters.reference_condition() ]),
            )
            panel_helpers.create_run_button(panel, main_sizer, from_gui_function=self.from_gui)
            
    @staticmethod
    def from_gui(frame):
        # 
        # get wig files
        # 
        combined_wig = gui.combined_wigs[-1]
        Method.inputs.combined_wig = combined_wig.main_path
        Method.inputs.metadata     = combined_wig.metadata.path
        
        # 
        # get annotation
        # 
        Method.inputs.annotation_path = gui.annotation_path
        transit_tools.validate_annotation(Method.inputs.annotation_path)
        
        # 
        # setup custom inputs
        # 
        for each_key, each_getter in Method.value_getters.items():
            try:
                Method.inputs[each_key] = each_getter()
            except Exception as error:
                raise Exception(f'''Failed to get value of "{each_key}" from GUI:\n{error}''')
        
        assert not Method.inputs.refs or Method.inputs.refs[0] in Method.inputs.included_conditions, f"Ref Condition '{Method.inputs.refs[0]}' is not one of the selected conditions: {Method.inputs.included_conditions}"
        assert len(Method.inputs.included_conditions) > 1, "please select more than one condition"
        
        # 
        # save result files
        # 
        Method.inputs.output_path = gui_tools.ask_for_output_file_path(
            default_file_name=f"{Method.cli_name}_output.csv",
            output_extensions='Common output extensions (*.csv,*.dat,*.txt,*.out)|*.csv;*.dat;*.txt;*.out;|\nAll files (*.*)|*.*',
        )
        if not Method.inputs.output_path:
            return None

        return Method

    @staticmethod
    @cli.add_command(cli_name)
    def from_args(args, kwargs):
        console_tools.handle_help_flag(kwargs, Method.usage_string)
        console_tools.handle_unrecognized_flags(Method.valid_cli_flags, kwargs, Method.usage_string)
        console_tools.enforce_number_of_args(args, Method.usage_string, at_least=4)
        
        combined_wig      = args[0]
        annotation_path   = args[2]
        metadata          = args[1]
        output_path       = args[3]
        normalization     = kwargs.get("n", Method.inputs.normalization)
        n_terminus        = float(kwargs.get("iN", Method.inputs.n_terminus))
        c_terminus        = float(kwargs.get("iC", Method.inputs.c_terminus))
        winz              = "winz" in kwargs
        pseudocount       = int(kwargs.get("PC", Method.inputs.pseudocount))
        alpha             = float(kwargs.get("alpha", Method.inputs.alpha))
        refs              = kwargs.get("-ref", Method.inputs.refs)  # list of condition names to use a reference for calculating lfc_s
        if refs != []: refs = refs.split(",")
        excluded_conditions = list( filter(None, kwargs.get("-exclude-conditions", "").split(",")) )
        included_conditions = list( filter(None, kwargs.get("-include-conditions", "").split(",")) )

        # save all the data
        Method.inputs.update(dict(
            combined_wig=combined_wig,
            metadata=metadata,
            annotation_path=annotation_path,
            normalization=normalization,
            output_path=output_path,
            
            excluded_conditions=excluded_conditions,
            included_conditions=included_conditions,
            n_terminus=n_terminus,
            c_terminus=c_terminus,
            pseudocount=pseudocount,
            winz=winz,
            refs=refs,
            alpha=alpha,
        ))
        
        Method.Run()
        
    def means_by_condition_for_gene(self, sites, conditions, data):
        """
            Returns a dictionary of {Condition: Mean} for each condition.
            ([Site], [Condition]) -> {Condition: Number}
            Site :: Number
            Condition :: String
        """
        n_ta_sites = len(sites)
        wigs_by_conditions = collections.defaultdict(lambda: [])
        for i, c in enumerate(conditions):
            wigs_by_conditions[c].append(i)

        return {
            c: numpy.mean(transit_tools.winsorize(data[wigIndex][:, sites]))
            if n_ta_sites > 0
            else 0
            for (c, wigIndex) in wigs_by_conditions.items()
        }

    def means_by_rv(self, data, rv_site_indexes_map, genes, conditions):
        """
            Returns Dictionary of mean values by condition
            ([[Wigdata]], {rv: SiteIndex}, [Gene], [Condition]) -> {rv: {Condition: Number}}
            Wigdata :: [Number]
            SiteIndex :: Number
            Gene :: {start, end, rv, gene, strand}
            Condition :: String
        """
        means_by_rv = {}
        for gene in genes:
            rv = gene["rv"]
            means_by_rv[rv] = self.means_by_condition_for_gene(
                rv_site_indexes_map[rv], conditions, data
            )
        return means_by_rv

    def group_by_condition(self, wig_list, conditions):
        """
            Returns array of datasets, where each dataset corresponds to one condition.
            ([[Wigdata]], [Condition]) -> [[DataForCondition]]
            Wigdata :: [Number]
            Condition :: String
            DataForCondition :: [Number]
        """
        counts_by_condition = collections.defaultdict(lambda: [])
        count_sum = 0
        for i, c in enumerate(conditions):
            count_sum += numpy.sum(wig_list[i])
            counts_by_condition[c].append(wig_list[i])

        return (
            count_sum,
            [numpy.array(v).flatten() for v in counts_by_condition.values()],
        )

    def calculate_anova(self, data, genes, means_by_rv, rv_site_indexes_map, conditions):
        """
            Runs Anova (grouping data by condition) and returns p and q values
            ([[Wigdata]], [Gene], {rv: {Condition: Mean}}, {rv: [SiteIndex]}, [Condition]) -> Tuple([Number], [Number])
            Wigdata :: [Number]
            Gene :: {start, end, rv, gene, strand}
            Mean :: Number
            SiteIndex: Integer
            Condition :: String
        """
        import scipy
        import scipy.stats
        import statsmodels.stats.multitest
        
        count = 0

        msrs, mses, f_stats, pvals, rvs, status = [],[],[],[],[],[]
        for _, gene in informative_iterator.ProgressBar(genes, title="Running Anova"):
            count += 1
            rv = gene["rv"]
            if len(rv_site_indexes_map[rv]) <= 1:
                status.append("TA sites <= 1")
                msr,mse,f_stat,pval = 0,0,-1,1
            else:
                count_sum, counts_vec = self.group_by_condition(
                    list(map(lambda wigData: wigData[rv_site_indexes_map[rv]], data)),
                    conditions,
                )
                if self.inputs.winz:
                    counts_vec = transit_tools.winsorize(counts_vec)

                if count_sum == 0:
                    msr,mse,f_stat,pval = 0,0,-1,1
                    status.append("No counts in all conditions")
                else:
                    f_stat,pval = scipy.stats.f_oneway(*counts_vec)
                    status.append("-")
                    # counts_vec is a list of numpy arrays, or could be a list of lists
                    # pooled counts for each condition, over TAs in gene and replicates
                    if isinstance(counts_vec[0],numpy.ndarray): 
                      counts_vec_as_arrays = counts_vec
                      counts_vecAsLists = [grp.tolist() for grp in counts_vec]
                    else:
                      counts_vec_as_arrays = [numpy.array(grp) for grp in counts_vec]
                      counts_vecAsLists = counts_vec
                    all_counts = [item for sublist in counts_vecAsLists for item in sublist]
                    grand_mean = numpy.mean(all_counts)
                    group_means = [numpy.mean(grp) for grp in counts_vec_as_arrays]
                    k,n = len(counts_vec),len(all_counts)
                    df_between,df_within = k-1,n-k
                    msr,mse = 0,0
                    for grp in counts_vec_as_arrays: msr += grp.size*(numpy.mean(grp)-grand_mean)**2/float(df_between)
                    for grp,mn in zip(counts_vec_as_arrays,group_means): mse += numpy.sum((grp-mn)**2) 
                    mse /= float(df_within)
                    mse = mse+self.inputs.alpha ### moderation
                    f_mod = msr/float(mse)
                    Pmod = scipy.stats.f.sf(f_mod, df_between, df_within)
                    f_stat,pval = f_mod,Pmod
            pvals.append(pval)   
            f_stats.append(f_stat) 
            msrs.append(msr)
            mses.append(mse)
            rvs.append(rv)

            # Update progress
            if gui.is_active:
                percentage = 100.0 * count / len(genes)
                progress_update(f"Running Anova Method... {percentage:5.1f}%", percentage)

        pvals = numpy.array(pvals)
        mask = numpy.isfinite(pvals)
        qvals = numpy.full(pvals.shape, numpy.nan)
        qvals[mask] = statsmodels.stats.multitest.fdrcorrection(pvals[mask])[1]  # BH, alpha=0.05

        msr, mse, f, p, q, status_map = {},{},{},{},{},{}
        for i,rv in enumerate(rvs):
            msr[rv], mse[rv], f[rv], p[rv], q[rv], status_map[rv] = msrs[i], mses[i], f_stats[i], pvals[i], qvals[i], status[i]
        return msr, mse, f, p, q, status_map
    
    def calc_lfcs(self, means, refs=[], pseudocount=5):
        if len(refs) == 0:
            refs = means  # if ref condition(s) not explicitly defined, use mean of all
        grand_mean = numpy.mean(refs)
        lfcs = [math.log((x + pseudocount) / float(grand_mean + pseudocount), 2) for x in means]
        return lfcs

    def Run(self):
        logging.log("Starting Anova analysis")
        start_time = time.time()
        
        # 
        # get data
        # 
        logging.log("Getting Data")
        if True:
            sites, data, filenames_in_comb_wig = tnseq_tools.CombinedWigData.load(self.inputs.combined_wig)
            
            logging.log(f"Normalizing using: {self.inputs.normalization}")
            data, factors = norm_tools.normalize_data(data, self.inputs.normalization)
            
            if self.inputs.winz: logging.log("Winsorizing insertion counts")
            conditions_by_wig_fingerprint, _, _, ordering_metadata = tnseq_tools.read_samples_metadata(self.inputs.metadata)
            conditions = [ conditions_by_wig_fingerprint.get(f, None) for f in filenames_in_comb_wig ]
            conditions_list = transit_tools.select_conditions(
                conditions=conditions,
                included_conditions=self.inputs.included_conditions,
                excluded_conditions=self.inputs.excluded_conditions,
                ordering_metadata=ordering_metadata,
            )

            condition_names = [conditions_by_wig_fingerprint[f] for f in filenames_in_comb_wig]
            # validate
            if self.inputs.refs and len(set(self.inputs.refs) - set(condition_names)) > 0:
                logging.error(f"One of the reference conditions {self.inputs.refs} is not one of the available conditions: {misc.no_duplicates(condition_names)}")

            (
                data,
                file_names,
                condition_names,
                conditions,
                _,
                _,
            ) = transit_tools.filter_wigs_by_conditions3(
                data,
                file_names=filenames_in_comb_wig, # it looks like file_names and condition_names have to be parallel to data (vector of wigs)
                condition_names=condition_names, # original Condition column in samples metadata file
                included_cond=self.inputs.included_conditions,
                excluded_cond=self.inputs.excluded_conditions,
                conditions=condition_names,
            ) # this is kind of redundant for ANOVA, but it is here because condition, covars, and interactions could have been manipulated for ZINB
            
            logging.log("reading genes")
            genes = tnseq_tools.read_genes(self.inputs.annotation_path)
        
        # 
        # process data
        # 
        if True:
            logging.log("processing data")
            TASiteindexMap = {ta: i for i, ta in enumerate(sites)}
            rv_site_indexes_map = tnseq_tools.rv_siteindexes_map(
                genes, TASiteindexMap, n_terminus=self.inputs.n_terminus, c_terminus=self.inputs.c_terminus
            )
            means_by_rv = self.means_by_rv(data, rv_site_indexes_map, genes, conditions)

            logging.log("Running Anova")
            msrs, mses, f_stats, pvals, qvals, run_status = self.calculate_anova(
                data, genes, means_by_rv, rv_site_indexes_map, conditions
            )
        
        # 
        # write output
        # 
        if True:
            logging.log(f"Adding File: {self.inputs.output_path}")
            
            # 
            # generate rows
            # 
            rows = []
            for gene in genes:
                each_rv = gene["rv"]
                if each_rv in means_by_rv:
                    means = [ means_by_rv[each_rv][condition_name] for condition_name in conditions_list]
                    refs  = [ means_by_rv[each_rv][ref_condition ] for ref_condition in self.inputs.refs]
                    lfcs = self.calc_lfcs(means, refs, self.inputs.pseudocount)
                    rows.append(
                        [
                            each_rv,
                            gene["gene"],
                            str(len(rv_site_indexes_map[each_rv])),
                        ] + [
                            "%0.2f" % x for x in means
                        ] + [
                            "%0.3f" % x for x in lfcs
                        ] +  [
                            "%f" % x for x in [msrs[each_rv], mses[each_rv], f_stats[each_rv], pvals[each_rv], qvals[each_rv]]
                        ] + [
                            run_status[each_rv]
                        ]
                    )
            
            # 
            # write to file
            # 
            transit_tools.write_result(
                path=self.inputs.output_path,
                file_kind=Method.identifier,
                rows=rows,
                column_names=[
                    "Rv",
                    "Gene",
                    "TAs",
                    *[ f"Mean {condition_name}" for condition_name in conditions_list ],
                    *[  f"LFC {condition_name}" for condition_name in conditions_list ],
                    "MSR",
                    "MSE With Alpha",
                    "Fstat",
                    "P Value",
                    "Adj P Value",
                    "Status"
                ],
                extra_info=dict(
                    parameters=dict(
                        conditions_list=conditions_list,
                        normalization=self.inputs.normalization,
                        trimming=f"{self.inputs.n_terminus}/{self.inputs.c_terminus} % (N/C)",
                        pseudocounts=self.inputs.pseudocount,
                        alpha=self.inputs.alpha,
                    ),
                ),
            )
            logging.log("Finished Anova analysis")
            logging.log(f"Time: {time.time() - start_time:0.1f}s\n")
        results_area.add(self.inputs.output_path)

@transit_tools.ResultsFile
class File:
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
                "Display Table": lambda *args: SpreadSheet(title=Method.name,heading=self.comments,column_names=self.column_names,rows=self.rows, sort_by=["Adj P Value", "P Value"]).Show(),
                "Display Heatmap": lambda *args: self.create_heatmap(infile=self.path, output_path=self.path+".heatmap.png"),
            })
        )
        
        # 
        # get column names
        # 
        comments, headers, rows = csv.read(self.path, seperator="\t", skip_empty_lines=True, comment_symbol="#")
        if len(comments) == 0:
            raise Exception(f'''No comments in file, and I expected the last comment to be the column names, while to load Anova file "{self.path}"''')
        self.column_names = comments[-1].split("\t")
        self.comments = "\n".join(comments)
        
        # 
        # get rows
        #
        self.rows = []
        for each_row in rows:
            self.rows.append({
                each_column_name: each_cell
                    for each_column_name, each_cell in zip(self.column_names, each_row)
            })
        
        # 
        # get summary stats
        #
        self.values_for_result_table.update({
            f"Gene Count": len(self.rows),
            f"Adj P Value < {Method.significance_threshold}": len([
                1 for each in self.rows
                    if each.get("Adj P Value", 1) < Method.significance_threshold 
            ]),
        })
    
    def __str__(self):
        return f"""
            File for {Method.identifier}
                path: {self.path}
                column_names: {self.column_names}
        """.replace('\n            ','\n').strip()
    
    def create_heatmap(self, infile, output_path, topk=-1, qval=0.05, low_mean_filter=5):
        with gui_tools.nice_error_log:
            transit_tools.require_r_to_be_installed()
            
            headers = None
            data, hits = [], []
            number_of_conditions = -1

            with open(infile) as file:
                for line in file:
                    w = line.rstrip().split("\t")
                    if line[0] == "#" or (
                        "P Value" in line and "Adj P Value" in line
                    ):  # check for 'pval' for backwards compatibility
                        headers = w
                        continue  # keep last comment line as headers
                    # assume first non-comment line is header
                    if number_of_conditions == -1:
                        # ANOVA header line has names of conditions, organized as 3+2*number_of_conditions+3 (2 groups (means, lfc_s) X number_of_conditions conditions)
                        number_of_conditions = int((len(w) - 6) / 2)
                        headers = headers[3 : 3 + number_of_conditions]
                        headers = [x.replace("Mean ", "") for x in headers]
                    else:
                        means = [
                            float(x) for x in w[3 : 3 + number_of_conditions]
                        ]  # take just the columns of means
                        lfcs = [
                            float(x) for x in w[3 + number_of_conditions : 3 + number_of_conditions + number_of_conditions]
                        ]  # take just the columns of lfc_s
                        each_qval = float(w[-2])
                        data.append((w, means, lfcs, each_qval))
            
            data.sort(key=lambda x: x[-1])
            hits, lfc_s = [], []
            for k, (w, means, lfcs, each_qval) in enumerate(data):
                if (topk == -1 and each_qval < qval) or (
                    topk != -1 and k < topk
                ):
                    mm = round(numpy.mean(means), 1)
                    if mm < low_mean_filter:
                        print("excluding %s/%s, mean(means)=%s" % (w[0], w[1], mm))
                    else:
                        hits.append(w)
                        lfc_s.append(lfcs)

            print("heatmap based on %s genes" % len(hits))
            gene_names = ["%s/%s" % (w[0], w[1]) for w in hits]
            hash = {}
            headers = [h.replace("Mean ", "") for h in headers]
            for i, col in enumerate(headers):
                hash[col] = FloatVector([x[i] for x in lfc_s])
            df = DataFrame(hash)
            transit_tools.r_heatmap_func(df, StrVector(gene_names), output_path)
            
            # add it as a result
            results_area.add(output_path)
            gui_tools.show_image(output_path)

