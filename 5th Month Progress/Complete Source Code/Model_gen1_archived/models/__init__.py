"""KANConvNet model package.

Importable surface:
    from models import KANConvNet
    from models.kan_layers import FourierKANLinear, KolmogorovActivation
    from models.kan_conv import KANConv1d
"""
from .kan_layers import FourierKANLinear, KolmogorovActivation
from .kan_conv import KANConv1d
from .kanconvnet import KANConvNet

__all__ = [
    "FourierKANLinear",
    "KolmogorovActivation",
    "KANConv1d",
    "KANConvNet",
]
