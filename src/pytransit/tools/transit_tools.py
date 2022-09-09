# Copyright 2015.
#   Michael A. DeJesus, Chaitra Ambadipudi, and  Thomas R. Ioerger.
#
#
#    This file is part of TRANSIT.
#
#    TRANSIT is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License.
#
#
#    TRANSIT is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with TRANSIT.  If not, see <http://www.gnu.org/licenses/>.

DEBUG = False
EOL = "\n"
SEPARATOR = "\1"  # for making names that combine conditions and interactions; try not to use a char a user might have in a condition name

import sys
import os
import math
import warnings
import ntpath
from typing import NamedTuple

import numpy
import scipy.optimize
import scipy.stats
import heapq

# 
# optional import: wx
# 
try:
    import wx
    import wx.xrc
    import wx.adv
    import wx.lib.mixins.listctrl as listmix
    from wx.lib.buttons import GenBitmapTextButton
    from pubsub import pub

    WX_VERSION = int(wx.version()[0])
    HAS_WX = True

except Exception as e:
    HAS_WX = False
    WX_VERSION = 0
    wx                  = None
    GenBitmapTextButton = None
    pub                 = None
    listmix             = None

# 
# optional import: R
# 
try:
    import rpy2.robjects
    from rpy2.robjects import (
        r,
        DataFrame,
        globalenv,
        IntVector,
        FloatVector,
        StrVector,
        packages as rpackages,
    )
    HAS_R = True
except Exception as e:
    HAS_R = False
    r = None
    DataFrame   = None
    globalenv   = None
    IntVector   = None
    FloatVector = None
    StrVector   = None
    rpackages   = None

import pytransit
import pytransit.tools.tnseq_tools as tnseq_tools
import pytransit.tools.norm_tools as norm_tools
import pytransit.basics.csv as csv
from pytransit.basics.lazy_dict import LazyDict
from pytransit.basics.named_list import named_list
from pytransit.tools.console_tools import clean_args

def write_dat(path, heading, table, eol="\n"):
    if len(heading) != 0:
        heading = "#" + heading
    heading = heading.replace("\n", "\n#")
    body = eol.join([ "\t".join(each_row) for each_row in table ])
    string = heading + eol + body
    with open(path, 'w') as outfile:
        outfile.write(string)

if HAS_WX:
    def subscribe(*args):
        """
        Summary:
            The old style:
                pub.subscribe(self.thing, "event_name")
            
            The new style enabled by this function:
                @subscribe("event_name")
                def thing(self, *args):
                    pass
        """
        def decorator(function_being_wrapped):
            pub.subscribe(function_being_wrapped, *args)
            return function_being_wrapped
        return decorator
    
    class AssumeZerosDialog(wx.Dialog):
        def __init__(self, *args, **kw):

            self.ID_HIMAR1 = wx.NewId()
            self.ID_TN5 = wx.NewId()

            wx.Dialog.__init__(self, None, title="Dialog")

            self.ID_HIMAR1 = wx.NewId()
            self.ID_TN5 = wx.NewId()

            self.SetSize((500, 300))
            self.SetTitle("Warning:  Wig Files Do Not Include Empty Sites")

            mainSizer = wx.BoxSizer(wx.VERTICAL)
            self.SetSizer(mainSizer)

            warningText = """

                One or more of your .wig files does not include any empty sites (i.e. sites with zero read-counts). The analysis methods in TRANSIT require knowing ALL possible insertion sites, even those without reads.
                    
                    Please indicate how you want to proceed:

                    As Himar1: You will need to provide the DNA sequence (.fasta format) and TRANSIT will automatically determine empty TA sites.

                    As Tn5: TRANSIT will assume all nucleotides are possible insertion sites. Those not included in the .wig file are assumed to be zero.
            """.replace("\n                ", "\n")
            warningStaticBox = wx.StaticText(
                self, wx.ID_ANY, warningText, (-1, -1), (-1, -1), wx.ALL
            )
            warningStaticBox.Wrap(480)
            mainSizer.Add(warningStaticBox, flag=wx.CENTER, border=5)

            button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            himar1Button = wx.Button(self, self.ID_HIMAR1, label="Proceed as Himar1")
            tn5Button = wx.Button(self, self.ID_TN5, label="Proceed as Tn5")
            cancelButton = wx.Button(self, wx.ID_CANCEL, label="Cancel")

            button_sizer.Add(himar1Button, flag=wx.LEFT, border=5)
            button_sizer.Add(tn5Button, flag=wx.LEFT, border=5)
            button_sizer.Add(cancelButton, flag=wx.LEFT, border=5)

            mainSizer.Add(
                button_sizer, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10
            )

            himar1Button.Bind(wx.EVT_BUTTON, self.OnClose)
            tn5Button.Bind(wx.EVT_BUTTON, self.OnClose)
            cancelButton.Bind(wx.EVT_BUTTON, self.OnClose)

        def OnClose(self, event):

            if self.IsModal():
                self.EndModal(event.EventObject.Id)
            else:
                self.Close()

working_directory = os.getcwd()

def fetch_name(filepath):
    return os.path.splitext(ntpath.basename(filepath))[0]

def basename(filepath):
    return ntpath.basename(filepath)

def dirname(filepath):
    return os.path.dirname(os.path.abspath(filepath))

def show_ask_warning(MSG=""):
    dial = wx.MessageDialog(None, MSG, "Warning", wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION)
    return dial.ShowModal()

def show_error_dialog(message):
    dial = wx.MessageDialog(None, message, "Error", wx.OK | wx.ICON_ERROR)
    dial.ShowModal()

def log(message, *args, **kwargs):
    import inspect
    import os
    message = f"{message} "+ " ".join([ f"{each}" for each in args])
    
    # get some context as to who is creating the message
    stack             = inspect.stack()
    caller_frame_info = stack[1]
    file_name         = ""
    caller_name       = ""
    try: file_name = os.path.basename(caller_frame_info.filename)
    except Exception as error: pass # sometimes the caller doesn't have a file name (ex: REPL)
    try: caller_name = caller_frame_info.function
    except Exception as error: pass # sometimes the caller doesn't have a function name (ex: lambda)
    
    # remove the .py extension
    if file_name[len(file_name)-3:len(file_name)] == ".py":
        file_name = file_name[0:len(file_name)-3]
    
    print(f'[{file_name}:{caller_name}()]', message, flush=True, **kwargs)
    if HAS_WX:
        import pytransit.tools.gui_tools as gui_tools
        gui_tools.set_status(message)
    
def transit_error(text):
    log(text)
    try:
        show_error_dialog(text)
    except:
        pass

def validate_annotation(annotation):
    if not annotation or not os.path.exists(annotation):
        transit_error("Error: No or Invalid annotation file selected!")
        return False
    return True

def validate_control_datasets(ctrldata):
    if len(ctrldata) == 0:
        transit_error("Error: No control datasets selected!")
        return False
    return True

def validate_both_datasets(ctrldata, expdata):
    if len(ctrldata) == 0 and len(expdata) == 0:
        transit_error("Error: No datasets selected!")
        return False
    elif len(ctrldata) == 0:
        transit_error("Error: No control datasets selected!")
        return False
    elif len(expdata) == 0:
        transit_error("Error: No experimental datasets selected!")
        return False
    else:
        return True

def validate_transposons_used(datasets, transposons, justWarn=True):
    # Check if transposon type is okay.
    unknown = tnseq_tools.get_unknown_file_types(datasets, transposons)
    if unknown:
        if justWarn:
            answer = show_ask_warning(
                "Warning: Some of the selected datasets look like they were created using transposons that this method was not intended to work with: %s. Proceeding may lead to errors. Click OK to continue."
                % (",".join(unknown))
            )
            if answer == wx.ID_CANCEL:
                return False
            else:
                return True
        else:
            transit_error(
                "Error: Some of the selected datasets look like they were created using transposons that this method was not intended to work with: %s."
                % (",".join(unknown))
            )
            return False

    return True

def validate_wig_format(wig_list, wxobj=None):
    # Check if the .wig files include zeros or not
    status = 0
    genome = ""
    includesZeros = tnseq_tools.check_wig_includes_zeros(wig_list)

    if sum(includesZeros) < len(includesZeros):
        # If console mode, just print(a warning)
        if not wxobj or not HAS_WX:
            warnings.warn(
                "\nOne or more of your .wig files does not include any empty sites (i.e. sites with zero read-counts). Proceeding as if data was Tn5 (all other sites assumed to be zero)!\n"
            )
            return (2, "")

        # Else check their decision
        dlg = AssumeZerosDialog()
        result = dlg.ShowModal()
        if result == dlg.ID_HIMAR1 and wxobj:
            status = 1
            # Get genome
            wc = u"Known Sequence Extensions (*.fna,*.fasta)|*.fna;*.fasta;|\nAll files (*.*)|*.*"
            gen_dlg = wx.FileDialog(
                wxobj,
                message="Save file as ...",
                defaultDir=os.getcwd(),
                defaultFile="",
                wildcard=wc,
                style=wx.FD_OPEN,
            )
            if gen_dlg.ShowModal() == wx.ID_OK:
                genome = gen_dlg.GetPath()
            else:
                genome = ""

        elif result == dlg.ID_TN5:
            status = 2
            genome = ""
        else:
            status = 3
            genome = ""
    return (status, genome)

def validate_filetypes(datasets, transposons, justWarn=True):
    validate_transposons_used(datasets, transposons, justWarn)

def get_pos_hash(path):
    """Returns a dictionary that maps coordinates to a list of genes that occur at that coordinate.
    
    Arguments:
        path (str): Path to annotation in .prot_table or GFF3 format.
    
    Returns:
        dict: Dictionary of position to list of genes that share that position.
    """
    filename, file_extension = os.path.splitext(path)
    if file_extension.lower() in [".gff", ".gff3"]:
        return tnseq_tools.get_pos_hash_gff(path)
    else:
        return tnseq_tools.get_pos_hash_pt(path)

def get_extended_pos_hash(path):
    """Returns a dictionary that maps coordinates to a list of genes that occur at that coordinate.

    Arguments:
        path (str): Path to annotation in .prot_table or GFF3 format.

    Returns:
        dict: Dictionary of position to list of genes that share that position.
    """
    filename, file_extension = os.path.splitext(path)
    if file_extension.lower() in [".gff", ".gff3"]:
        return tnseq_tools.get_extended_pos_hash_gff(path)
    else:
        return tnseq_tools.get_extended_pos_hash_pt(path)

def get_gene_info(path):
    """Returns a dictionary that maps gene id to gene information.
    
    Arguments:
        path (str): Path to annotation in .prot_table or GFF3 format.
    
    Returns:
        dict: Dictionary of gene id to tuple of information:
            - name
            - description
            - start coordinate
            - end coordinate
            - strand
            
    """
    filename, file_extension = os.path.splitext(path)
    if file_extension.lower() in [".gff", ".gff3"]:
        return tnseq_tools.get_gene_info_gff(path)
    else:
        return tnseq_tools.get_gene_info_pt(path)

def convert_to_combined_wig(dataset_list, annotationPath, outputPath, normchoice="nonorm"):
    """Normalizes the input datasets and outputs the result in CombinedWig format.
    
    Arguments:
        dataset_list (list): List of paths to datasets in .wig format
        annotationPath (str): Path to annotation in .prot_table or GFF3 format.
        outputPath (str): Desired output path.
        normchoice (str): Choice for normalization method.
            
    """

    (fulldata, position) = tnseq_tools.CombinedWig.gather_wig_data(dataset_list)
    (fulldata, factors) = norm_tools.normalize_data(
        fulldata, normchoice, dataset_list, annotationPath
    )
    position = position.astype(int)

    hash = get_pos_hash(annotationPath)
    rv2info = get_gene_info(annotationPath)

    output = open(outputPath, "w")
    output.write("#Converted to CombinedWig with TRANSIT.\n")
    if normchoice != "nonorm":
        output.write("#Reads normalized using '%s'\n" % normchoice)
        if type(factors[0]) == type(0.0):
            output.write(
                "#Normalization Factors: %s\n"
                % "\t".join(["%s" % f for f in factors.flatten()])
            )
        else:
            output.write(
                "#Normalization Factors: %s\n"
                % " ".join([",".join(["%s" % bx for bx in b]) for b in factors])
            )

    (K, N) = fulldata.shape
    output.write("#Files:\n")
    for f in dataset_list:
        output.write("#%s\n" % f)

    for i, pos in enumerate(position):
        # output.write("%-10d %s  %s\n" % (position[i], "".join(["%7.1f" % c for c in fulldata[:,i]]),",".join(["%s (%s)" % (orf,rv2info.get(orf,["-"])[0]) for orf in hash.get(position[i], [])])   ))
        output.write(
            "%d\t%s\t%s\n"
            % (
                position[i],
                "\t".join(["%1.1f" % c for c in fulldata[:, i]]),
                ",".join(
                    [
                        "%s (%s)" % (orf, rv2info.get(orf, ["-"])[0])
                        for orf in hash.get(position[i], [])
                    ]
                ),
            )
        )
    output.close()

def get_validated_data(wig_list, wxobj=None):
    """ Returns a tuple of (data, position) containing a matrix of raw read-counts
        , and list of coordinates. 

    Arguments:
        wig_list (list): List of paths to wig files.
        wxobj (object): wxPython GUI object for warnings

    Returns:
        tuple: Two lists containing data and positions of the wig files given.

    :Example:

        >>> import pytransit.tools.tnseq_tools as tnseq_tools
        >>> (data, position) = tnseq_tools.get_validated_data(["data/glycerol_H37Rv_rep1.wig", "data/glycerol_H37Rv_rep2.wig"])
        >>> print(data)
        array([[ 0.,  0.,  0., ...,  0.,  0.,  0.],
               [ 0.,  0.,  0., ...,  0.,  0.,  0.]])

    .. seealso:: :class:`get_file_types` :class:`combine_replicates` :class:`get_data_zero_fill` :class:`pytransit.tools.norm_tools.normalize_data`
    """
    (status, genome) = validate_wig_format(wig_list, wxobj=wxobj)

    # Regular file with empty sites
    if status == 0:
        return tnseq_tools.CombinedWig.gather_wig_data(wig_list)
    # No empty sites, decided to proceed as Himar1
    elif status == 1:
        return tnseq_tools.get_data_w_genome(wig_list, genome)
    # No empty sites, decided to proceed as Tn5
    elif status == 2:
        return tnseq_tools.get_data_zero_fill(wig_list)
    # Didn't choose either.... what!?
    else:
        return tnseq_tools.CombinedWig.gather_wig_data([])

def get_transposons_text(transposons):
    if len(transposons) == 0:
        return "Tn attribute missing!"
    elif len(transposons) == 1:
        return "Intended for %s only" % transposons[0]
    elif len(transposons) == 2:
        return "Intended for %s or %s" % tuple(transposons)
    else:
        return (
            "Intended for "
            + ", ".join(transposons[:-1])
            + ", and "
            + transposons[-1]
        )

def r_heatmap_func(*args):
    raise Exception(f'''R is not installed, cannot create heatmap without R''')
if HAS_R:
    # Create the R function
    r("""
        make_heatmap = function(lfcs,genenames,outfilename) { 
        rownames(lfcs) = genenames
        suppressMessages(require(gplots))
        colors <- colorRampPalette(c("red", "white", "blue"))(n = 200)

        C = length(colnames(lfcs))
        R = length(rownames(lfcs))
        W = 300+C*30
        H = 300+R*15

        png(outfilename,width=W,height=H)
        #defaults are lwid=lhei=c(1.5,4)
        #heatmap.2(as.matrix(lfcs),col=colors,margin=c(12,12),lwid=c(2,6),lhei=c(0.1,2),trace="none",cexCol=1.4,cexRow=1.4,key=T) # make sure white=0
        #heatmap.2(as.matrix(lfcs),col=colors,margin=c(12,12),trace="none",cexCol=1.2,cexRow=1.2,key=T) # make sure white=0 # setting margins was causing failures, so remove it 8/22/21
        heatmap.2(as.matrix(lfcs),col=colors,margin=c(12,12),trace="none",cexCol=1.2,cexRow=1.2,key=T) # actually, margins was OK, so the problem must have been with lhei and lwid
        dev.off()
        }
    """.replace("    \n", "\n"))
    r_heatmap_func = globalenv["make_heatmap"]

# 
# Results read/write
# 
if True:
    result_file_classes = []
    def ResultsFile(a_class):
        """
        @ResultsFile
        class File:
            @staticmethod
            def can_load(args):
                return False
        """
        if not callable(getattr(a_class, "can_load", None)):
            raise Exception(f"""Everything that usese ResultsFile should have a can_load() static method, but {a_class} does not""")
        
        result_file_classes.append(a_class)
        return a_class
    
    def file_starts_with(path, identifier):
        with open(path) as in_file:
            for line in in_file:
                if line.startswith(identifier):
                    return True
                break
        return False
    
    def read_result(path):
        result_object = None
        for FileClass in result_file_classes:
            loadable = None
            try:
                loadable = FileClass.can_load(path)
            except Exception as error:
                print(error)
            if loadable:
                result_object = FileClass(path=path)
        
        return result_object

    def write_result(*, path, file_kind, extra_info, column_names, rows):
        assert file_kind.isidentifier(), f"The file_kind {file_kind} must not contain whitespace or anything else that makes it an invalid var name"
        
        import ez_yaml
        import pytransit.basics.csv as csv
        from pytransit.basics.misc import indent
        ez_yaml.yaml.version = None # disable the "%YAML 1.2\n" header
        
        extra_info = extra_info or {}
        
        # 
        # write to file
        # 
        csv.write(
            path=path,
            seperator="\t",
            comment_symbol="#",
            comments=[
                file_kind, # identifier always comes first
                f"yaml:",
                f"    Console Command: python3 {' '.join(sys.argv)}",
                indent(ez_yaml.to_string(extra_info), by="    "),
                "\t".join(column_names) # column names always last
            ],
            rows=rows,
        )

# input: conditions are per wig; orderingMetdata comes from tnseq_tools.read_samples_metadata()
# output: conditionsList is selected subset of conditions (unique, in preferred order)
def filter_wigs_by_conditions(
    data,
    conditions,
    covariates=[],
    interactions=[],
    excluded_conditions=[],
    included_conditions=[],
    unknown_cond_flag="FLAG-UNMAPPED-CONDITION-IN-WIG",
):
    """
        Filters conditions that are excluded/included.
        ([[Wigdata]], [Condition], [[Covar]], [Condition], [Condition]) -> Tuple([[Wigdata]], [Condition])
    """
    excluded_conditions, included_conditions = (
        set(excluded_conditions),
        set(included_conditions),
    )
    d_filtered, cond_filtered, filtered_indexes = [], [], []

    if len(excluded_conditions) > 0 and len(included_conditions) > 0:
        raise Exception(f'''Both excluded and included conditions have len > 0''')
    elif len(excluded_conditions) > 0:
        transit_tools.log("conditions excluded: {0}".format(excluded_conditions))
        for i, c in enumerate(conditions):
            if (c != unknown_cond_flag) and (c not in excluded_conditions):
                d_filtered.append(data[i])
                cond_filtered.append(conditions[i])
                filtered_indexes.append(i)
    elif len(included_conditions) > 0:
        transit_tools.log("conditions included: {0}".format(included_conditions))
        for i, c in enumerate(conditions):
            if (c != unknown_cond_flag) and (c in included_conditions):
                d_filtered.append(data[i])
                cond_filtered.append(conditions[i])
                filtered_indexes.append(i)
    else:
        for i, c in enumerate(conditions):
            if c != unknown_cond_flag:
                d_filtered.append(data[i])
                cond_filtered.append(conditions[i])
                filtered_indexes.append(i)

    covariates_filtered = [[c[i] for i in filtered_indexes] for c in covariates]
    interactions_filtered = [[c[i] for i in filtered_indexes] for c in interactions]

    return (
        numpy.array(d_filtered),
        numpy.array(cond_filtered),
        numpy.array(covariates_filtered),
        numpy.array(interactions_filtered),
    )

def select_conditions(conditions, included_conditions, excluded_conditions, ordering_metadata):
    if len(included_conditions) > 0:
        conditions_list = included_conditions
    else:
        conditions_list = []
        for each_condition in ordering_metadata[
            "condition"
        ]:  # the order conds appear in metadata file, duplicated for each sample
            if each_condition not in conditions_list:
                conditions_list.append(each_condition)
    for each_condition in excluded_conditions:
        if each_condition in conditions_list:
            conditions_list.remove(each_condition)
    
    return conditions_list

def filter_wigs_by_conditions2(data, conditions, conditionsList, covariates=[], interactions=[]):
    """
        Filters conditions that are excluded/included.
        ([[Wigdata]], [Condition], [[Covar]], [Condition], [Condition]) -> Tuple([[Wigdata]], [Condition])
    """
    d_filtered, cond_filtered, filtered_indexes = [], [], []

    for i, c in enumerate(conditions):
        if (c != unknown_cond_flag) and (c in conditionsList):
            d_filtered.append(data[i])
            cond_filtered.append(conditions[i])
            filtered_indexes.append(i)

    covariates_filtered = [[c[i] for i in filtered_indexes] for c in covariates]
    interactions_filtered = [[c[i] for i in filtered_indexes] for c in interactions]

    return (
        numpy.array(d_filtered),
        numpy.array(cond_filtered),
        numpy.array(covariates_filtered),
        numpy.array(interactions_filtered),
    )

def filter_wigs_by_conditions3(
    data,
    file_names,
    condition_names,
    included_cond,
    excluded_cond,
    conditions,
    covariates=[],
    interactions=[],
):
    """
        Filters conditions that are excluded/included; also extract cond, covar, and interaction labels
        condition_names: based on original Conditions column in metadata
        conditions: user might have specified an alternative column to analyze (list of labels parallel to wigs)
    """
    (
        file_names_filtered,
        cond_names_filtered,
        d_filtered,
        cond_filtered,
        filtered_indexes,
    ) = ([], [], [], [], [])

    for i in range(len(data)):
        if (
            len(included_cond) == 0 or condition_names[i] in included_cond
        ) and condition_names[i] not in excluded_cond:
            d_filtered.append(data[i])
            file_names_filtered.append(file_names[i])
            cond_names_filtered.append(condition_names[i])
            cond_filtered.append(conditions[i])
            filtered_indexes.append(i)

    covariates_filtered = [[c[i] for i in filtered_indexes] for c in covariates]
    interactions_filtered = [[c[i] for i in filtered_indexes] for c in interactions]

    return (
        numpy.array(d_filtered),
        numpy.array(file_names_filtered),
        numpy.array(cond_names_filtered),
        numpy.array(cond_filtered),
        numpy.array(covariates_filtered),
        numpy.array(interactions_filtered),
    )

# return a hash table of parallel lists, indexed by column header
def get_samples_metadata(metadata):
    data = {}
    header = None
    with open(metadata) as file:
        for line in file:
            if line[0] == "#":
                continue
            w = line.rstrip().split("\t")
            if header == None:
                header = w
                for col in header:
                    data[col] = []
            else:
                for i in range(len(header)):
                    data[header[i]].append(w[i])
    return data

def winsorize(counts):
    # input is insertion counts for gene: list of lists: n_replicates (rows) X n_TA sites (cols) in gene
    unique_counts = numpy.unique(numpy.concatenate(counts))
    if len(unique_counts) < 2:
        return counts
    else:
        n, n_minus_1 = unique_counts[
            heapq.nlargest(2, range(len(unique_counts)), unique_counts.take)
        ]
        result = [
            [n_minus_1 if count == n else count for count in wig] for wig in counts
        ]
        return numpy.array(result)

def gather_sample_data_for(conditions=None, wig_ids=None, wig_fingerprints=None, selected_samples=False):
    from pytransit.universal_data import universal
    from pytransit.tools.tnseq_tools import Wig
    
    wig_objects = universal.session_data.samples
    # default to all samples unless selected_samples is true
    if selected_samples:
        wig_objects = universal.session_data.selected_samples
    
    # filter by conditions if needed
    if conditions:
        condition_names = [ (each if isinstance(each, str) else each.name) for each in conditions ]
        wig_objects = [ each for each in wig_objects if each.extra_data.get("condition", None) in condition_names ]
    
    # filter by wig_ids if needed
    if wig_ids:
        wig_objects = [ each for each in wig_objects if each.id in wig_ids ]
    
    # filter by wig_fingerprints if needed
    if wig_fingerprints:
        wig_objects = [ each for each in wig_objects if each.id in wig_fingerprints ]
    
    return Wig.selected_as_gathered_data(wig_objects)