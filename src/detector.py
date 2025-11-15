"""
Motor de detecção de árvores - VERSÃO OTIMIZADA
"""

import cv2
import numpy as np
from PIL import Image
import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import *


class TreeDetector:
    """Motor de detecção de árvores com otimizações para movimento"""

    def __init__(self, similarity_threshold=SIMILARITY_THRESHOLD):
        self.templates = []
        self.similarity_threshold = similarity_threshold
        self.save_folder = SAVE_FOLDER

        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)

        # Thread pool para processamento paralelo
        if USE_THREADING:
            self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        else:
            self.executor = None

        self.load_templates()

    def add_template(self, image_pil):
        """Adiciona um novo exemplo de árvore"""
        img_array = np.array(image_pil)
        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Salvar arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{self.save_folder}/tree_{timestamp}.png"
        image_pil.save(filename)

        # Pré-processar e cachear escalas
        scaled_templates = self._preprocess_template(img_gray)

        self.templates.append({
            'image': img_gray,
            'scaled': scaled_templates,
            'size': img_gray.shape,
            'path': filename
        })

        print(f"✅ Template #{len(self.templates)} adicionado: {img_gray.shape}")

    def _preprocess_template(self, template):
        """Pré-processa template em múltiplas escalas (CACHE)"""
        scaled = {}
        for scale in SCALES:
            w = int(template.shape[1] * scale)
            h = int(template.shape[0] * scale)

            if w >= MIN_TEMPLATE_SIZE and h >= MIN_TEMPLATE_SIZE:
                scaled[scale] = cv2.resize(template, (w, h))

        return scaled

    def _get_roi(self, screen_shape, custom_roi=None):
        """Calcula ROI (Region of Interest) - região central ou customizada"""
        if not USE_ROI:
            return None

        # Usar ROI customizada se fornecida
        if USE_CUSTOM_ROI and custom_roi:
            return custom_roi

        # Caso contrário, calcular área central automaticamente
        h, w = screen_shape[:2]

        pad_w = int(w * ROI_PADDING)
        pad_h = int(h * ROI_PADDING)

        x1 = pad_w
        y1 = pad_h
        x2 = w - pad_w
        y2 = h - pad_h

        return (x1, y1, x2, y2)

    def detect(self, screenshot_pil, custom_roi=None):
        """
        Detecta árvores na screenshot - VERSÃO ULTRA OTIMIZADA
        - ROI para processar só área central ou customizada
        - Threading para processar templates em paralelo
        - Cache de templates preprocessados
        - NMS eficiente
        """
        if not self.templates:
            return []

        # Converter screenshot
        screen_array = np.array(screenshot_pil)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)

        # Aplicar ROI (customizada ou automática)
        roi = self._get_roi(screen_gray.shape, custom_roi)
        if roi:
            x1, y1, x2, y2 = roi
            screen_roi = screen_gray[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            screen_roi = screen_gray
            offset_x, offset_y = 0, 0

        # Downsample se configurado
        if DOWNSAMPLE_FACTOR < 1.0:
            new_w = int(screen_roi.shape[1] * DOWNSAMPLE_FACTOR)
            new_h = int(screen_roi.shape[0] * DOWNSAMPLE_FACTOR)
            screen_roi = cv2.resize(screen_roi, (new_w, new_h))
            scale_back = 1.0 / DOWNSAMPLE_FACTOR
        else:
            scale_back = 1.0

        # Detectar usando threading ou sequencial
        if USE_THREADING and self.executor:
            detections = self._detect_parallel(screen_roi, offset_x, offset_y, scale_back)
        else:
            detections = self._detect_sequential(screen_roi, offset_x, offset_y, scale_back)

        # NMS para remover duplicatas
        detections = self._non_maximum_suppression(detections)

        return detections

    def _detect_parallel(self, screen_roi, offset_x, offset_y, scale_back):
        """Detecta usando múltiplas threads"""
        detections = []
        futures = []

        # Submeter cada template para uma thread
        for idx, template_data in enumerate(self.templates):
            future = self.executor.submit(
                self._match_template,
                screen_roi,
                template_data,
                idx,
                offset_x,
                offset_y,
                scale_back
            )
            futures.append(future)

        # Coletar resultados
        for future in as_completed(futures):
            detections.extend(future.result())

        return detections

    def _detect_sequential(self, screen_roi, offset_x, offset_y, scale_back):
        """Detecta sequencialmente (fallback)"""
        detections = []

        for idx, template_data in enumerate(self.templates):
            matches = self._match_template(
                screen_roi,
                template_data,
                idx,
                offset_x,
                offset_y,
                scale_back
            )
            detections.extend(matches)

        return detections

    def _match_template(self, screen_roi, template_data, idx, offset_x, offset_y, scale_back):
        """Faz template matching para um template específico"""
        detections = []

        # Usar templates pré-processados (cache)
        for scale, resized_template in template_data['scaled'].items():
            w, h = resized_template.shape[1], resized_template.shape[0]

            # Verificar se template cabe na ROI
            if w > screen_roi.shape[1] or h > screen_roi.shape[0]:
                continue

            # Aplicar downsample no template se necessário
            if scale_back != 1.0:
                w_scaled = int(w * (1.0 / scale_back))
                h_scaled = int(h * (1.0 / scale_back))
                if w_scaled < MIN_TEMPLATE_SIZE or h_scaled < MIN_TEMPLATE_SIZE:
                    continue
                template_to_match = cv2.resize(resized_template, (w_scaled, h_scaled))
            else:
                template_to_match = resized_template

            # Template matching
            result = cv2.matchTemplate(screen_roi, template_to_match, cv2.TM_CCOEFF_NORMED)

            # Encontrar matches acima do threshold
            locations = np.where(result >= self.similarity_threshold)

            for pt in zip(*locations[::-1]):
                x, y = pt
                confidence = result[y, x]

                # Ajustar coordenadas (ROI + downsample)
                final_x = int(x * scale_back) + offset_x
                final_y = int(y * scale_back) + offset_y
                final_w = int(w * scale_back)
                final_h = int(h * scale_back)

                detections.append({
                    'x': final_x,
                    'y': final_y,
                    'w': final_w,
                    'h': final_h,
                    'confidence': float(confidence),
                    'template_id': idx
                })

        return detections

    def _non_maximum_suppression(self, detections):
        """Remove detecções duplicadas de forma eficiente"""
        if not detections:
            return []

        # Ordenar por confiança (maior primeiro)
        detections.sort(key=lambda x: x['confidence'], reverse=True)

        kept = []

        for det in detections:
            # Verificar se está muito próximo de alguma detecção já mantida
            is_duplicate = False
            for kept_det in kept:
                dx = abs(det['x'] - kept_det['x'])
                dy = abs(det['y'] - kept_det['y'])

                if dx < DUPLICATE_DISTANCE and dy < DUPLICATE_DISTANCE:
                    is_duplicate = True
                    break

            if not is_duplicate:
                kept.append(det)

        return kept

    def load_templates(self):
        """Carrega templates salvos"""
        if not os.path.exists(self.save_folder):
            print("⚠️ Pasta tree_training_data não encontrada!")
            return

        files = [f for f in os.listdir(self.save_folder) if f.endswith('.png')]

        if not files:
            print("⚠️ Nenhuma imagem .png encontrada!")
            return

        print(f"\n🔍 Carregando templates de: {self.save_folder}")

        for filename in sorted(files):
            filepath = os.path.join(self.save_folder, filename)
            try:
                img = Image.open(filepath)
                img_array = np.array(img)

                # Converter para grayscale
                if len(img_array.shape) == 3:
                    img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    img_gray = img_array

                # Pré-processar
                scaled_templates = self._preprocess_template(img_gray)

                self.templates.append({
                    'image': img_gray,
                    'scaled': scaled_templates,
                    'size': img_gray.shape,
                    'path': filepath
                })

                print(f"  ✅ {filename} → {img_gray.shape}")

            except Exception as e:
                print(f"  ❌ Erro em {filename}: {e}")

        print(f"\n📚 TOTAL: {len(self.templates)} templates carregados!")
        print(f"🎯 Threshold: {self.similarity_threshold}")
        print(f"⚡ Threading: {'ATIVO' if USE_THREADING else 'DESATIVADO'}")
        print(f"🎯 ROI: {'ATIVO' if USE_ROI else 'DESATIVADO'}")
        print(f"🚀 FPS Target: {FPS_TARGET}")

    def save_config(self):
        """Salva configurações"""
        config = {
            'num_templates': len(self.templates),
            'threshold': self.similarity_threshold,
            'scales': SCALES,
            'fps_target': FPS_TARGET,
            'use_roi': USE_ROI,
            'use_threading': USE_THREADING
        }
        with open(f"{self.save_folder}/config.json", 'w') as f:
            json.dump(config, f, indent=2)

    def cleanup(self):
        """Limpa recursos"""
        if self.executor:
            self.executor.shutdown(wait=False)
