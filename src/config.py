"""
Configurações do sistema de detecção de árvores PXG
"""

# DETECÇÃO
SIMILARITY_THRESHOLD = 0.52  # Mais sensível para compensar otimizações
SCALES = [1.0]  # APENAS escala original = 3x mais rápido!
MIN_TEMPLATE_SIZE = 10
DUPLICATE_DISTANCE = 50  # Distância mínima entre detecções

# PERFORMANCE - CONFIGURAÇÃO ULTRA RÁPIDA 🚀
FPS_TARGET = 35  # FPS aumentado para máxima fluidez
DETECTION_DELAY = 1.0 / FPS_TARGET  # ~0.029s por frame
USE_ROI = True  # Usar apenas região central da tela
ROI_PADDING = 0.4  # 40% de padding (processar apenas 20% CENTRAL = MUITO MAIS RÁPIDO)
DOWNSAMPLE_FACTOR = 0.75  # Reduz resolução em 25% para processar mais rápido
USE_THREADING = True  # Processar templates em paralelo
MAX_WORKERS = 6  # Mais threads para processamento paralelo

# PASTAS
SAVE_FOLDER = 'tree_training_data'
CONFIG_FILE = 'roi_config.json'  # Arquivo para salvar ROI customizada

# ROI CUSTOMIZADA
USE_CUSTOM_ROI = True  # Usar ROI customizada (se existir)
CUSTOM_ROI = None  # Será carregado do arquivo JSON (x1, y1, x2, y2)

# OVERLAY
OVERLAY_ALPHA = 0.3
DETECTION_COLOR = 'red'
DETECTION_WIDTH = 3
CAPTURE_COLOR = 'lime'
CAPTURE_WIDTH = 3
ROI_COLOR = 'cyan'  # Cor da área ROI
ROI_CAPTURE_COLOR = 'yellow'  # Cor ao capturar ROI
FONT_SIZE = 12

# HOTKEYS
HOTKEY_CAPTURE = 'subtract'  # NUMPAD [-] - Capturar template de árvore
HOTKEY_DETECT = 'add'        # NUMPAD [+] - Ativar/Pausar detecção
HOTKEY_SET_ROI = 'end'       # END - Definir área ROI customizada
HOTKEY_QUIT = '*'            # NUMPAD [*] - Sair
