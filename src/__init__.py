"""
Sistema de Detecção de Árvores PXG
Versão otimizada para detecção em movimento
"""

__version__ = "2.0.0"
__author__ = "PXG Tree Detector"

from src.detector import TreeDetector
from src.overlay import OverlayWindow
from src.config import *

__all__ = ['TreeDetector', 'OverlayWindow']
