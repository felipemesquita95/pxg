#!/usr/bin/env python3
"""
🌳 SISTEMA DE DETECÇÃO DE ÁRVORES PXG - VERSÃO 2.0 OTIMIZADA
Detecta árvores em MOVIMENTO com alta performance

Melhorias:
- ⚡ Threading para processamento paralelo
- 🎯 ROI (Region of Interest) para processar apenas área relevante
- 💾 Cache de templates preprocessados
- 🚀 FPS aumentado de ~10 para 25+
- 🧹 Código modularizado e organizado
"""

from src.detector import TreeDetector
from src.overlay import OverlayWindow
from src.config import SIMILARITY_THRESHOLD


def main():
    """Função principal"""
    print("🌳 Iniciando Tree Detector v2.0...")

    # Criar detector otimizado
    detector = TreeDetector(similarity_threshold=SIMILARITY_THRESHOLD)

    if not detector.templates:
        print("\n⚠️ NENHUM TEMPLATE CARREGADO!")
        print("   Verifique se a pasta 'tree_training_data' existe")
        print("   e contém arquivos .png\n")
        print("   Use NUMPAD [-] para capturar novos templates!\n")

    # Criar overlay
    overlay = OverlayWindow(detector)

    # Iniciar
    try:
        overlay.run()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    finally:
        detector.cleanup()
        print("✅ Encerrado")


if __name__ == "__main__":
    main()
