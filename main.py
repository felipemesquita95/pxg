"""
🌳 SISTEMA DE DETECÇÃO DE ÁRVORES PXG - VERSÃO BALANCEADA
Detecta BEM e RÁPIDO
"""

import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageGrab
import tkinter as tk
from tkinter import Canvas
import keyboard
import threading
import time
from datetime import datetime
import os
import json


class TreeDetector:
    """Motor de detecção de árvores"""
    
    def __init__(self, similarity_threshold=0.6):
        self.templates = []
        self.similarity_threshold = similarity_threshold
        self.save_folder = 'tree_training_data'
        
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)
        
        self.load_templates()
    
    def add_template(self, image_pil):
        """Adiciona um novo exemplo de árvore"""
        img_array = np.array(image_pil)
        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{self.save_folder}/tree_{timestamp}.png"
        image_pil.save(filename)
        
        self.templates.append({
            'image': img_gray,
            'size': img_gray.shape,
            'path': filename
        })
        
        print(f"✅ Template #{len(self.templates)} adicionado: {img_gray.shape}")
    
    def detect(self, screenshot_pil):
        """Detecta árvores na screenshot - VERSÃO ORIGINAL OTIMIZADA"""
        if not self.templates:
            return []
        
        # Converter screenshot para array
        screen_array = np.array(screenshot_pil)
        screen_gray = cv2.cvtColor(screen_array, cv2.COLOR_RGB2GRAY)
        
        detections = []
        
        # Testar cada template
        for idx, template_data in enumerate(self.templates):
            template = template_data['image']
            
            # Multi-scale template matching
            for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
                # Redimensionar template
                w = int(template.shape[1] * scale)
                h = int(template.shape[0] * scale)
                
                if w > screen_gray.shape[1] or h > screen_gray.shape[0]:
                    continue
                
                if w < 10 or h < 10:
                    continue
                
                resized_template = cv2.resize(template, (w, h))
                
                # Template matching
                result = cv2.matchTemplate(screen_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                
                # Encontrar matches acima do threshold
                locations = np.where(result >= self.similarity_threshold)
                
                for pt in zip(*locations[::-1]):
                    x, y = pt
                    confidence = result[y, x]
                    
                    # Verificar se não está muito próximo de outra detecção
                    is_duplicate = False
                    for det in detections:
                        if abs(det['x'] - x) < 50 and abs(det['y'] - y) < 50:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        detections.append({
                            'x': x,
                            'y': y,
                            'w': w,
                            'h': h,
                            'confidence': float(confidence),
                            'template_id': idx
                        })
        
        return detections
    
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
                
                # Converter para grayscale se necessário
                if len(img_array.shape) == 3:
                    img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    img_gray = img_array
                
                self.templates.append({
                    'image': img_gray,
                    'size': img_gray.shape,
                    'path': filepath
                })
                
                print(f"  ✅ {filename} → {img_gray.shape}")
                
            except Exception as e:
                print(f"  ❌ Erro em {filename}: {e}")
        
        print(f"\n📚 TOTAL: {len(self.templates)} templates carregados!")
        
        if self.templates:
            print(f"🎯 Threshold atual: {self.similarity_threshold}")
    
    def save_config(self):
        """Salva configurações"""
        config = {
            'num_templates': len(self.templates),
            'threshold': self.similarity_threshold
        }
        with open(f"{self.save_folder}/config.json", 'w') as f:
            json.dump(config, f)


class OverlayWindow:
    """Janela transparente overlay"""
    
    def __init__(self, detector):
        self.detector = detector
        
        self.mode = 'idle'
        self.capturing = False
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None
        
        self.root = tk.Tk()
        self.root.title("Tree Detector Overlay")
        
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-transparentcolor', 'white')
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        self.canvas = Canvas(
            self.root,
            width=screen_width,
            height=screen_height,
            bg='white',
            highlightthickness=0
        )
        self.canvas.pack()
        
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        
        self.status_text = self.canvas.create_text(
            10, 10, text="", anchor='nw',
            font=('Arial', 14, 'bold'), fill='lime'
        )
        
        # FPS/Stats
        self.stats_text = self.canvas.create_text(
            10, 100, text="", anchor='nw',
            font=('Arial', 12, 'bold'), fill='yellow'
        )
        self.detection_count = 0
        self.last_fps_time = time.time()
        self.fps = 0
        
        self.detecting = False
        self.detection_thread = None
        
        self.setup_hotkeys()
        self.update_status()
        
        print("\n" + "="*60)
        print("🌳 SISTEMA DE DETECÇÃO DE ÁRVORES - VERSÃO BALANCEADA")
        print("="*60)
        print("NUMPAD [-] - Modo CAPTURA (marcar árvore)")
        print("NUMPAD [+] - Ativar/Pausar DETECÇÃO")
        print("NUMPAD [*] - SAIR")
        print(f"📚 Templates: {len(self.detector.templates)}")
        print("="*60 + "\n")
    
    def setup_hotkeys(self):
        keyboard.add_hotkey('subtract', self.toggle_capture_mode)
        keyboard.add_hotkey('add', self.toggle_detection_mode)
        keyboard.add_hotkey('*', self.quit)
    
    def toggle_capture_mode(self):
        if self.mode == 'capturing':
            self.mode = 'idle'
            self.root.attributes('-transparentcolor', 'white')
            print("⏸️ Modo captura DESATIVADO")
        else:
            self.mode = 'capturing'
            self.detecting = False
            self.root.attributes('-transparentcolor', '')
            self.canvas.delete('all')
            self.status_text = self.canvas.create_text(
                10, 10, text="", anchor='nw',
                font=('Arial', 14, 'bold'), fill='lime'
            )
            self.stats_text = self.canvas.create_text(
                10, 100, text="", anchor='nw',
                font=('Arial', 12, 'bold'), fill='yellow'
            )
            print("🎯 Modo CAPTURA ativado!")
    
    def toggle_detection_mode(self):
        if not self.detector.templates:
            print("⚠️ Nenhum template! Use NUMPAD [-] para capturar.")
            return
        
        self.detecting = not self.detecting
        
        if self.detecting:
            self.mode = 'detecting'
            self.root.attributes('-transparentcolor', 'white')
            print(f"🔍 DETECÇÃO ATIVADA!")
            print(f"   Templates: {len(self.detector.templates)}")
            print(f"   Threshold: {self.detector.similarity_threshold}")
            
            self.detection_count = 0
            self.last_fps_time = time.time()
            
            if not self.detection_thread or not self.detection_thread.is_alive():
                self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
                self.detection_thread.start()
        else:
            self.mode = 'idle'
            print("⏸️ Detecção PAUSADA")
            self.canvas.delete('detection')
    
    def on_click(self, event):
        if self.mode != 'capturing':
            return
        self.capturing = True
        self.start_x = event.x
        self.start_y = event.y
        if self.current_rect:
            self.canvas.delete(self.current_rect)
    
    def on_drag(self, event):
        if not self.capturing:
            return
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline='lime', width=3
        )
    
    def on_release(self, event):
        if not self.capturing:
            return
        self.capturing = False
        
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        
        width = x2 - x1
        height = y2 - y1
        
        if width < 10 or height < 10:
            print("❌ Região muito pequena!")
            self.canvas.delete(self.current_rect)
            return
        
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        self.detector.add_template(screenshot)
        
        self.canvas.delete(self.current_rect)
        confirm_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline='green', width=5
        )
        self.root.after(500, lambda: self.canvas.delete(confirm_rect))
        
        print(f"✅ Árvore capturada! Total: {len(self.detector.templates)}")
        
        self.mode = 'idle'
        self.root.attributes('-transparentcolor', 'white')
    
    def detection_loop(self):
        """Loop de detecção - OTIMIZADO só no delay!"""
        while self.detecting:
            try:
                loop_start = time.time()
                
                # Capturar tela
                screenshot = ImageGrab.grab()
                
                # Detectar
                detections = self.detector.detect(screenshot)
                
                # Calcular FPS
                elapsed = time.time() - loop_start
                self.fps = 1.0 / elapsed if elapsed > 0 else 0
                
                # Atualizar UI
                self.root.after(0, self.draw_detections, detections)
                
                # AQUI ESTÁ A OTIMIZAÇÃO: delay de 0.1s ao invés de 0.5s
                time.sleep(0.1)  # 100ms = ~10 detecções por segundo
                
            except Exception as e:
                print(f"❌ Erro: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.5)
    
    def draw_detections(self, detections):
        self.canvas.delete('detection')
        
        for det in detections:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            conf = det['confidence']
            
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline='red', width=3, tags='detection'
            )
            
            self.canvas.create_text(
                x, y - 10, text=f"🌳 {conf:.0%}",
                anchor='sw', font=('Arial', 12, 'bold'),
                fill='red', tags='detection'
            )
        
        # Atualizar stats
        if detections:
            self.detection_count += len(detections)
        
        self.canvas.itemconfig(
            self.stats_text,
            text=f"FPS: {self.fps:.1f}\nDetecções agora: {len(detections)}\nTotal: {self.detection_count}"
        )
    
    def update_status(self):
        status_lines = []
        
        if self.mode == 'capturing':
            status_lines.append("🎯 MODO CAPTURA")
            status_lines.append("Arraste um quadrado")
        elif self.mode == 'detecting':
            status_lines.append("🔍 DETECTANDO...")
            status_lines.append(f"Templates: {len(self.detector.templates)}")
        else:
            status_lines.append("⏸️ PAUSADO")
            status_lines.append(f"Templates: {len(self.detector.templates)}")
        
        status_lines.append("")
        status_lines.append("[-]=Capturar | [+]=Detectar | [*]=Sair")
        
        self.canvas.itemconfig(self.status_text, text="\n".join(status_lines))
        self.root.after(100, self.update_status)
    
    def quit(self):
        print("\n💾 Salvando...")
        self.detector.save_config()
        print("👋 Até logo!")
        self.detecting = False
        self.root.quit()
    
    def run(self):
        self.root.mainloop()


def main():
    print("🌳 Iniciando Tree Detector...")
    
    # THRESHOLD: 0.6 = padrão, 0.55 = mais sensível, 0.7 = menos sensível
    detector = TreeDetector(similarity_threshold=0.6)
    
    if not detector.templates:
        print("\n⚠️ NENHUM TEMPLATE CARREGADO!")
        print("   Verifique se a pasta 'tree_training_data' existe")
        print("   e contém arquivos .png\n")
    
    overlay = OverlayWindow(detector)
    overlay.run()


if __name__ == "__main__":
    main()
