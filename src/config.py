"""
Configurações do sistema de detecção de árvores PXG
"""

# DETECÇÃO
SIMILARITY_THRESHOLD = 0.55  # Reduzido para detectar em movimento (era 0.6)
SCALES = [0.9, 1.0, 1.1]  # Reduzido de 5 para 3 escalas
MIN_TEMPLATE_SIZE = 10
DUPLICATE_DISTANCE = 50  # Distância mínima entre detecções

# PERFORMANCE
FPS_TARGET = 25  # Aumentado de ~10 para 25
DETECTION_DELAY = 1.0 / FPS_TARGET  # ~0.04s por frame
USE_ROI = True  # Usar apenas região central da tela
ROI_PADDING = 0.3  # 30% de padding (processar 60% central da tela)
DOWNSAMPLE_FACTOR = 1.0  # 1.0 = sem downsample, 0.5 = metade da resolução
USE_THREADING = True  # Processar templates em paralelo
MAX_WORKERS = 4  # Threads para processamento paralelo

# PASTAS
SAVE_FOLDER = 'tree_training_data'

# OVERLAY
OVERLAY_ALPHA = 0.3
DETECTION_COLOR = 'red'
DETECTION_WIDTH = 3
CAPTURE_COLOR = 'lime'
CAPTURE_WIDTH = 3
FONT_SIZE = 12

# HOTKEYS (numpad)
HOTKEY_CAPTURE = 'subtract'  # NUMPAD [-]
HOTKEY_DETECT = 'add'        # NUMPAD [+]
HOTKEY_QUIT = '*'            # NUMPAD [*]
