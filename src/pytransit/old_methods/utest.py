from pytransit.components.parameter_panel import panel, progress_update
import pytransit.components.results_area as results_area
import sys

from pytransit.tools.transit_tools import HAS_WX, wx, GenBitmapTextButton, pub

import os
import time
import ntpath
import math
import random
import numpy
import scipy.stats
import datetime

from pytransit.old_methods import analysis_base as base
import pytransit
from pytransit.tools import transit_tools
from pytransit.tools import tnseq_tools
from pytransit.tools import norm_tools
from pytransit.tools import stat_tools


############# GUI ELEMENTS ##################

short_name = "utest"
long_name = "Mann-Whitney U-test "
short_desc = "Mann-Whitney U-test of conditional essentiality between two conditions"
long_desc = """Mann-Whitney U-test for determining conditional essentiality. Based on rank order statistics to identify significant changes in mean read-counts between two conditions."""

transposons = ["himar1", "tn5"]
columns = [
    "Orf",
    "Name",
    "Desc",
    "Sites",
    "Mean Ctrl",
    "Mean Exp",
    "Log 2 FC",
    "U Statistic",
    "P Value",
    "Adj P Value",
]


class Analysis(base.TransitAnalysis):
    def __init__(self):
        base.TransitAnalysis.__init__(
            self,
            short_name,
            long_name,
            short_desc,
            long_desc,
            transposons,
            UTestMethod,
            UTestGUI,
            [UTestFile],
        )


############# FILE ##################


class UTestFile(base.TransitFile):
    def __init__(self):
        base.TransitFile.__init__(self, "#utest", columns)

    def get_header(self, path):
        DE = 0
        poslogfc = 0
        neglogfc = 0
        with open(path) as file:
            for line in file:
                if line.startswith("#"):
                    continue
                tmp = line.strip().split("\t")
                if float(tmp[-1]) < 0.05:
                    DE += 1
                    if float(tmp[-4]) > 0:
                        poslogfc += 1
                    else:
                        neglogfc += 1

        text = """Results:
    Conditionally - Essentials: %s
        Less Essential in Experimental datasets: %s
        More Essential in Experimental datasets: %s
            """ % (
            DE,
            poslogfc,
            neglogfc,
        )
        return text

    def get_menus(self):
        menus = []
        menus.append(("Display in Track View", self.display_in_track_view))
        return menus


############# GUI ##################


class UTestGUI(base.AnalysisGUI):
    def define_panel(self, wxobj):
        self.wxobj = wxobj
        utestPanel = wx.Panel(
            self.wxobj,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.TAB_TRAVERSAL,
        )

        utestSizer = wx.BoxSizer(wx.VERTICAL)

        utestLabel = wx.StaticText(
            utestPanel, wx.ID_ANY, "utest Options", wx.DefaultPosition, (120, -1), 0
        )
        utestLabel.SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        utestSizer.Add(utestLabel, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        utestTopSizer = wx.BoxSizer(wx.HORIZONTAL)

        utestTopSizer2 = wx.BoxSizer(wx.HORIZONTAL)

        utestLabelSizer = wx.BoxSizer(wx.VERTICAL)

        mainSizer1 = wx.BoxSizer(wx.VERTICAL)

        # (, , Sizer) = self.defineChoiceBox(utestPanel, "", "", "")
        # mainSizer1.Add(Sizer, 1, wx.EXPAND, 5 )

        # Norm
        utestNormChoiceChoices = [
            "TTR",
            "nzmean",
            "totreads",
            "zinfnb",
            "quantile",
            "betageom",
            "nonorm",
        ]
        (utestNormLabel, self.wxobj.utestNormChoice, normSizer) = self.defineChoiceBox(
            utestPanel,
            "Normalization:",
            utestNormChoiceChoices,
            "Choice of normalization method. The default choice, 'TTR', normalizes datasets to have the same expected count (while not being sensative to outliers). Read documentation for a description other methods. ",
        )
        mainSizer1.Add(normSizer, 1, wx.EXPAND, 5)

        utestSizer.Add(mainSizer1, 1, wx.EXPAND, 5)

        # LOESS Check
        (self.wxobj.utestLoessCheck, loessCheckSizer) = self.defineCheckBox(
            utestPanel,
            labelText="Correct for Genome Positional Bias",
            widgetCheck=False,
            widgetSize=(-1, -1),
            tooltipText="Check to correct read-counts for possible regional biase using LOESS. Clicking on the button below will plot a preview, which is helpful to visualize the possible bias in the counts.",
        )
        utestSizer.Add(loessCheckSizer, 0, wx.EXPAND, 5)

        # LOESS Button
        self.wxobj.utestLoessPrev = wx.Button(
            utestPanel,
            wx.ID_ANY,
            "Preview LOESS fit",
            wx.DefaultPosition,
            wx.DefaultSize,
            0,
        )
        utestSizer.Add(self.wxobj.utestLoessPrev, 0, wx.ALL | wx.CENTER, 5)

        # Zeros Check
        (self.wxobj.utestZeroCheckBox, zeroSizer) = self.defineCheckBox(
            utestPanel,
            labelText="Include sites with all zeros",
            widgetCheck=True,
            widgetSize=(-1, -1),
            tooltipText="Includes sites that are empty (zero) accross all datasets. Unchecking this may be useful for tn5 datasets, where all nucleotides are possible insertion sites and will have a large number of empty sites (significantly slowing down computation and affecting estimates).",
        )
        utestSizer.Add(zeroSizer, 0, wx.EXPAND, 5)

        utestButton = wx.Button(
            utestPanel, wx.ID_ANY, "Run U-test", wx.DefaultPosition, wx.DefaultSize, 0
        )
        utestSizer.Add(utestButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        utestPanel.SetSizer(utestSizer)
        utestPanel.Layout()
        utestSizer.Fit(utestPanel)

        # Connect events
        utestButton.Bind(wx.EVT_BUTTON, self.wxobj.RunMethod)
        self.wxobj.utestLoessPrev.Bind(wx.EVT_BUTTON, self.wxobj.when_loess_prev_clicked)

        self.panel = utestPanel


########## CLASS #######################


class UTestMethod(base.DualConditionMethod):
    """
    U-test

    """

    def __init__(
        self,
        ctrldata,
        expdata,
        annotation_path,
        output_file,
        normalization="TTR",
        includeZeros=False,
        replicates="Sum",
        LOESS=False,
        ignore_codon=True,
        n_terminus=0.0,
        c_terminus=0.0,
        wxobj=None,
    ):

        base.DualConditionMethod.__init__(
            self,
            short_name,
            long_name,
            short_desc,
            long_desc,
            ctrldata,
            expdata,
            annotation_path,
            output_file,
            normalization=normalization,
            replicates=replicates,
            LOESS=LOESS,
            n_terminus=n_terminus,
            c_terminus=c_terminus,
            wxobj=wxobj,
        )

        self.includeZeros = includeZeros

    @classmethod
    def from_gui(self, wxobj):
        """ """
        # Get Annotation file
        from pytransit.globals import gui, cli, root_folder, debugging_enabled
        annotation_path = gui.annotation_path
        if not transit_tools.validate_annotation(annotation_path):
            return None

        # Get selected files
        ctrldata = wxobj.ctrlSelected()
        expdata = wxobj.expSelected()
        if not transit_tools.validate_both_datasets(ctrldata, expdata):
            return None

        # Validate transposon types
        if not transit_tools.validate_transposons_used(ctrldata + expdata, transposons):
            return None

        # Read the parameters from the wxPython widgets
        ignore_codon = True
        normalization = wxobj.utestNormChoice.GetString(
            wxobj.utestNormChoice.GetCurrentSelection()
        )
        replicates = None

        includeZeros = wxobj.utestZeroCheckBox.GetValue()

        n_terminus = float(wxobj.globalNTerminusText.GetValue())
        c_terminus = float(wxobj.globalCTerminusText.GetValue())
        LOESS = wxobj.utestLoessCheck.GetValue()

        # Get output path
        defaultFileName = "utest_%s_output" % (normalization)
        if includeZeros:
            defaultFileName += "_iz"
        defaultFileName += ".dat"

        defaultDir = os.getcwd()
        output_path = wxobj.SaveFile(defaultDir, defaultFileName)
        if not output_path:
            return None
        output_file = open(output_path, "w")

        return self(
            ctrldata,
            expdata,
            annotation_path,
            output_file,
            normalization,
            includeZeros,
            replicates,
            LOESS,
            ignore_codon,
            n_terminus,
            c_terminus,
            wxobj,
        )

    @classmethod
    def from_args(self, args, kwargs):

        ctrldata = args[0].split(",")
        expdata = args[1].split(",")
        annotation_path = args[2]
        output_path = args[3]
        output_file = open(output_path, "w")

        normalization = kwargs.get("n", "TTR")
        includeZeros = kwargs.get("iz", False)
        replicates = None

        LOESS = kwargs.get("l", False)
        ignore_codon = True
        n_terminus = float(kwargs.get("iN", 0.00))
        c_terminus = float(kwargs.get("iC", 0.00))

        return self(
            ctrldata,
            expdata,
            annotation_path,
            output_file,
            normalization,
            includeZeros,
            replicates,
            LOESS,
            ignore_codon,
            n_terminus,
            c_terminus,
        )

    def Run(self):

        logging.log("Starting Mann-Whitney U-test Method")
        start_time = time.time()

        Kctrl = len(self.ctrldata)
        Kexp = len(self.expdata)
        # Get orf data
        logging.log("Getting Data")
        (data, position) = transit_tools.get_validated_data(
            self.ctrldata + self.expdata, wxobj=self.wxobj
        )

        (K, N) = data.shape

        if self.normalization != "nonorm":
            logging.log("Normalizing using: %s" % self.normalization)
            (data, factors) = norm_tools.normalize_data(
                data,
                self.normalization,
                self.ctrldata + self.expdata,
                self.annotation_path,
            )

        if self.LOESS:
            logging.log("Performing LOESS Correction")
            for j in range(K):
                data[j] = stat_tools.loess_correction(position, data[j])

        G = tnseq_tools.Genes(
            self.ctrldata + self.expdata,
            self.annotation_path,
            ignore_codon=self.ignore_codon,
            n_terminus=self.n_terminus,
            c_terminus=self.c_terminus,
            data=data,
            position=position,
        )

        # u-test
        data = []
        N = len(G)
        count = 0
        
        for gene in G:
            count += 1
            if gene.k == 0 or gene.n == 0:
                (test_obs, mean1, mean2, log2FC, u_stat, pval_2tail) = (
                    0,
                    0,
                    0,
                    0,
                    0.0,
                    1.00,
                )
            else:

                if not self.includeZeros:
                    ii = numpy.sum(gene.reads, 0) > 0
                else:
                    ii = numpy.ones(gene.n) == 1

                data1 = gene.reads[:Kctrl, ii].flatten()
                data2 = gene.reads[Kctrl:, ii].flatten()
                try:
                    u_stat, pval_2tail = scipy.stats.mannwhitneyu(
                        data1, data2, alternative="two-sided"
                    )
                except ValueError as e:
                    u_stat, pval_2tail = 0.0, 1.00

                n1 = len(data1)
                n2 = len(data2)

                mean1 = 0
                if n1 > 0:
                    mean1 = numpy.mean(data1)
                mean2 = 0
                if n2 > 0:
                    mean2 = numpy.mean(data2)

                try:
                    # Only adjust log2FC if one of the means is zero
                    if mean1 > 0 and mean2 > 0:
                        log2FC = math.log((mean2) / (mean1), 2)
                    else:
                        log2FC = math.log((mean2 + 1.0) / (mean1 + 1.0), 2)
                except:
                    log2FC = 0.0

            # ["Orf","Name","Desc","Sites","Mean Ctrl","Mean Exp","log2FC", "U-Statistic","P Value","Adj P value"]

            data.append(
                [
                    gene.orf,
                    gene.name,
                    gene.desc,
                    gene.n,
                    mean1,
                    mean2,
                    log2FC,
                    u_stat,
                    pval_2tail,
                ]
            )

            # Update Progress
            percent = (100.0 * count / N)
            text = "Running Mann-Whitney U-test Method... %1.1f%%" % percent
            progress_update(text, percent)

        #
        logging.log("")  # Printing empty line to flush stdout
        logging.log("Performing Benjamini-Hochberg Correction")
        data.sort()
        qval = stat_tools.bh_fdr_correction([row[-1] for row in data])

        self.output.write("#utest\n")
        if self.wxobj:
            members = sorted(
                [
                    attr
                    for attr in dir(self)
                    if not callable(getattr(self, attr)) and not attr.startswith("__")
                ]
            )
            memberstr = ""
            for m in members:
                memberstr += "%s = %s, " % (m, getattr(self, m))
            self.output.write(
                "#GUI with: norm=%s, includeZeros=%s, output=%s\n"
                % (
                    self.normalization,
                    self.includeZeros,
                    self.output.name.encode("utf-8"),
                )
            )
        else:
            self.output.write("#Console: python3 %s\n" % " ".join(sys.argv))
        self.output.write(
            "#Control Data: %s\n" % (",".join(self.ctrldata).encode("utf-8"))
        )
        self.output.write(
            "#Experimental Data: %s\n" % (",".join(self.expdata).encode("utf-8"))
        )
        self.output.write(
            "#Annotation path: %s\n" % (self.annotation_path.encode("utf-8"))
        )
        self.output.write("#Time: %s\n" % (time.time() - start_time))
        self.output.write("#%s\n" % "\t".join(columns))

        for i, row in enumerate(data):
            (orf, name, desc, n, mean1, mean2, log2FC, u_stat, pval_2tail) = row
            self.output.write(
                "%s\t%s\t%s\t%d\t%1.1f\t%1.1f\t%1.2f\t%1.2f\t%1.5f\t%1.5f\n"
                % (
                    orf,
                    name,
                    desc,
                    n,
                    mean1,
                    mean2,
                    log2FC,
                    u_stat,
                    pval_2tail,
                    qval[i],
                )
            )
        self.output.close()

        logging.log("Adding File: %s" % (self.output.name))
        results_area.add(self.output.name)
        self.finish()
        logging.log("Finished Mann-Whitney U-test Method")

    usage_string = """python3 %s utest <comma-separated .wig control files> <comma-separated .wig experimental files> <annotation .prot_table or GFF3> <output file> [Optional Arguments]

        Optional Arguments:
        -n <string>     :=  Normalization method. Default: -n TTR
        -iz             :=  Include rows with zero accross conditions.
        -l              :=  Perform LOESS Correction; Helps remove possible genomic position bias. Default: Turned Off.
        -iN <float>     :=  Ignore TAs occuring at given fraction (as integer) of the N terminus. Default: -iN 0
        -iC <float>     :=  Ignore TAs occuring at given fraction (as integer) of the C terminus. Default: -iC 0
        """ % sys.argv[0]

