methods = {}
from .anova              import Analysis; methods["anova"             ] = Analysis()
from .binomial           import Analysis; methods["binomial"          ] = Analysis()
from .corrplot           import Analysis; methods["corrplot"          ] = Analysis()
from .GI_gui             import Analysis; methods["GI_gui"            ] = Analysis()
from .griffin            import Analysis; methods["griffin"           ] = Analysis()
from .gumbel             import Analysis; methods["gumbel"            ] = Analysis()
from .heatmap            import Analysis; methods["heatmap"           ] = Analysis()
from .hmm                import Analysis; methods["hmm"               ] = Analysis()
from .normalize          import Analysis; methods["normalize"         ] = Analysis()
from .pathway_enrichment import Analysis; methods["pathway_enrichment"] = Analysis()
from .rankproduct        import Analysis; methods["rankproduct"       ] = Analysis()
from .resampling         import Analysis; methods["resampling"        ] = Analysis()
from .tn5gaps            import Analysis; methods["tn5gaps"           ] = Analysis()
from .tnseq_stats_gui    import Analysis; methods["tnseq_stats_gui"   ] = Analysis()
from .ttnfitness         import Analysis; methods["ttnfitness"        ] = Analysis()
from .utest              import Analysis; methods["utest"             ] = Analysis()
from .zinb               import Analysis; methods["zinb"              ] = Analysis()