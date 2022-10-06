methods = {}
from .anova              import Analysis; methods["anova"              ] = Analysis()
from .corrplot           import Analysis; methods["corrplot"           ] = Analysis()
from .gi                 import Analysis; methods["gi"                 ] = Analysis()
from .gumbel             import Analysis; methods["gumbel"             ] = Analysis()
from .hmm                import Analysis; methods["hmm"                ] = Analysis()
from .pathway_enrichment import Analysis; methods["pathway_enrichment" ] = Analysis()
from .resampling         import Analysis; methods["resampling"         ] = Analysis()
from .tnseq_stats        import Analysis; methods["tnseq_stats"        ] = Analysis()
from .ttnfitness         import Analysis; methods["ttnfitness"         ] = Analysis()
from .zinb               import Analysis; methods["zinb"               ] = Analysis()