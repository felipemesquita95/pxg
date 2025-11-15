"""
Interface overlay transparente para captura e visualização
"""

import tkinter as tk
from tkinter import Canvas
from PIL import ImageGrab
import keyboard
import threading
import time
import json
import os
import winsound  # Para tocar som no Windows
from src.config import *


class OverlayWindow:
    """Janela transparente overlay - VERSÃO OTIMIZADA"""

    def __init__(self, detector):
        self.detector = detector

        self.mode = 'idle'
        self.capturing = False
        self.capturing_roi = False  # Modo de captura de ROI
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None

        # ROI customizada
        self.custom_roi = None
        self.load_custom_roi()  # Carregar ROI salva

        # Tkinter setup
        self.root = tk.Tk()
        self.root.title("Tree Detector Overlay")

        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', OVERLAY_ALPHA)
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

        # Mouse events
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

        # Status text
        self.status_text = self.canvas.create_text(
            10, 10, text="", anchor='nw',
            font=('Arial', 14, 'bold'), fill='lime'
        )

        # Stats text
        self.stats_text = self.canvas.create_text(
            10, 100, text="", anchor='nw',
            font=('Arial', FONT_SIZE, 'bold'), fill='yellow'
        )

        # Performance tracking
        self.detection_count = 0
        self.total_detections = 0
        self.last_fps_time = time.time()
        self.fps = 0
        self.frame_times = []

        # Detection state
        self.detecting = False
        self.detection_thread = None

        # ROI visualization
        self.roi_rect = None

        self.setup_hotkeys()
        self.update_status()

        self._print_banner()

    def _print_banner(self):
        """Imprime banner de inicialização"""
        print("\n" + "="*60)
        print("🌳 SISTEMA DE DETECÇÃO DE ÁRVORES - VERSÃO OTIMIZADA")
        print("="*60)
        print(f"NUMPAD [-] - Modo CAPTURA (marcar árvore)")
        print(f"NUMPAD [+] - Ativar/Pausar DETECÇÃO")
        print(f"END - Definir ÁREA ROI (região de detecção)")
        print(f"NUMPAD [*] - SAIR")
        print(f"📚 Templates: {len(self.detector.templates)}")
        print(f"⚡ FPS Target: {FPS_TARGET}")

        if self.custom_roi:
            x1, y1, x2, y2 = self.custom_roi
            w, h = x2 - x1, y2 - y1
            print(f"🎯 ROI Customizada: {w}x{h} px (salva)")
        else:
            print(f"🎯 ROI: {'AUTO' if USE_ROI else 'DESATIVADO'}")

        print(f"🚀 Threading: {'ATIVO' if USE_THREADING else 'DESATIVADO'}")
        print("="*60 + "\n")

    def setup_hotkeys(self):
        """Configura atalhos de teclado"""
        keyboard.add_hotkey(HOTKEY_CAPTURE, self.toggle_capture_mode)
        keyboard.add_hotkey(HOTKEY_DETECT, self.toggle_detection_mode)
        keyboard.add_hotkey(HOTKEY_SET_ROI, self.toggle_roi_capture_mode)
        keyboard.add_hotkey(HOTKEY_QUIT, self.quit)

    def load_custom_roi(self):
        """Carrega ROI customizada do arquivo JSON"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.custom_roi = tuple(config.get('custom_roi', None))
                    if self.custom_roi:
                        print(f"✅ ROI customizada carregada: {self.custom_roi}")
        except Exception as e:
            print(f"⚠️ Erro ao carregar ROI: {e}")
            self.custom_roi = None

    def save_custom_roi(self):
        """Salva ROI customizada no arquivo JSON"""
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)

            config['custom_roi'] = list(self.custom_roi) if self.custom_roi else None

            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"💾 ROI customizada salva: {self.custom_roi}")
        except Exception as e:
            print(f"❌ Erro ao salvar ROI: {e}")

    def toggle_capture_mode(self):
        """Ativa/desativa modo captura"""
        if self.mode == 'capturing':
            self.mode = 'idle'
            self.root.attributes('-transparentcolor', 'white')
            print("⏸️ Modo captura DESATIVADO")
        else:
            self.mode = 'capturing'
            self.detecting = False
            self.root.attributes('-transparentcolor', '')
            self.canvas.delete('all')

            # Recriar textos
            self.status_text = self.canvas.create_text(
                10, 10, text="", anchor='nw',
                font=('Arial', 14, 'bold'), fill='lime'
            )
            self.stats_text = self.canvas.create_text(
                10, 100, text="", anchor='nw',
                font=('Arial', FONT_SIZE, 'bold'), fill='yellow'
            )

            print("🎯 Modo CAPTURA ativado!")

    def toggle_roi_capture_mode(self):
        """Ativa/desativa modo captura de ROI"""
        if self.mode == 'capturing_roi':
            self.mode = 'idle'
            self.root.attributes('-transparentcolor', 'white')
            print("⏸️ Modo captura ROI DESATIVADO")
        else:
            self.mode = 'capturing_roi'
            self.detecting = False
            self.root.attributes('-transparentcolor', '')
            self.canvas.delete('all')

            # Recriar textos
            self.status_text = self.canvas.create_text(
                10, 10, text="", anchor='nw',
                font=('Arial', 14, 'bold'), fill='yellow'
            )
            self.stats_text = self.canvas.create_text(
                10, 100, text="", anchor='nw',
                font=('Arial', FONT_SIZE, 'bold'), fill='yellow'
            )

            print("🎯 Modo CAPTURA ROI ativado!")
            print("   Arraste um retângulo definindo a área de detecção")

    def toggle_detection_mode(self):
        """Ativa/desativa modo detecção"""
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
            print(f"   FPS Target: {FPS_TARGET}")

            # Reset stats
            self.detection_count = 0
            self.total_detections = 0
            self.last_fps_time = time.time()
            self.frame_times = []

            # Desenhar ROI se ativo
            if USE_ROI:
                self._draw_roi_indicator()

            # Iniciar thread de detecção
            if not self.detection_thread or not self.detection_thread.is_alive():
                self.detection_thread = threading.Thread(
                    target=self.detection_loop,
                    daemon=True
                )
                self.detection_thread.start()
        else:
            self.mode = 'idle'
            print("⏸️ Detecção PAUSADA")
            print(f"   Total detectado: {self.total_detections}")
            print(f"   FPS médio: {self._get_avg_fps():.1f}")
            self.canvas.delete('detection')
            self.canvas.delete('roi')

    def _draw_roi_indicator(self):
        """Desenha indicador visual da ROI (customizada ou automática)"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Usar ROI customizada se existir
        if self.custom_roi:
            x1, y1, x2, y2 = self.custom_roi
            roi_label = "🎯 ÁREA DE DETECÇÃO (ROI CUSTOMIZADA)"
        else:
            # ROI automática baseada em padding
            pad_w = int(screen_width * ROI_PADDING)
            pad_h = int(screen_height * ROI_PADDING)

            x1 = pad_w
            y1 = pad_h
            x2 = screen_width - pad_w
            y2 = screen_height - pad_h
            roi_label = "🎯 ÁREA DE DETECÇÃO (ROI AUTOMÁTICA)"

        self.roi_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=ROI_COLOR, width=2, dash=(5, 5), tags='roi'
        )

        # Texto explicativo
        self.canvas.create_text(
            (x1 + x2) // 2, y1 - 20,
            text=roi_label,
            font=('Arial', 12, 'bold'),
            fill=ROI_COLOR, tags='roi'
        )

    def on_click(self, event):
        """Mouse click - inicia captura (template ou ROI)"""
        if self.mode not in ['capturing', 'capturing_roi']:
            return

        if self.mode == 'capturing':
            self.capturing = True
        elif self.mode == 'capturing_roi':
            self.capturing_roi = True

        self.start_x = event.x
        self.start_y = event.y
        if self.current_rect:
            self.canvas.delete(self.current_rect)

    def on_drag(self, event):
        """Mouse drag - desenha retângulo"""
        if not (self.capturing or self.capturing_roi):
            return
        if self.current_rect:
            self.canvas.delete(self.current_rect)

        # Cor diferente para ROI
        color = ROI_CAPTURE_COLOR if self.capturing_roi else CAPTURE_COLOR

        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline=color, width=CAPTURE_WIDTH
        )

    def on_release(self, event):
        """Mouse release - captura template ou ROI"""
        if not (self.capturing or self.capturing_roi):
            return

        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        width = x2 - x1
        height = y2 - y1

        # MODO: Captura de ROI
        if self.capturing_roi:
            self.capturing_roi = False

            if width < 50 or height < 50:
                print(f"❌ ROI muito pequena! Mínimo: 50x50")
                self.canvas.delete(self.current_rect)
                return

            # Salvar ROI
            self.custom_roi = (x1, y1, x2, y2)
            self.save_custom_roi()

            # Feedback visual
            self.canvas.delete(self.current_rect)
            confirm_rect = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline='green', width=5
            )
            self.root.after(500, lambda: self.canvas.delete(confirm_rect))

            print(f"✅ ROI definida: {width}x{height} px")
            print(f"   Coordenadas: ({x1}, {y1}) → ({x2}, {y2})")

            self.mode = 'idle'
            self.root.attributes('-transparentcolor', 'white')
            return

        # MODO: Captura de Template
        if self.capturing:
            self.capturing = False

            if width < MIN_TEMPLATE_SIZE or height < MIN_TEMPLATE_SIZE:
                print(f"❌ Região muito pequena! Mínimo: {MIN_TEMPLATE_SIZE}x{MIN_TEMPLATE_SIZE}")
                self.canvas.delete(self.current_rect)
                return

            # Capturar screenshot da região
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            self.detector.add_template(screenshot)

            # Feedback visual
            self.canvas.delete(self.current_rect)
            confirm_rect = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline='green', width=5
            )
            self.root.after(500, lambda: self.canvas.delete(confirm_rect))

            print(f"✅ Árvore capturada! Total: {len(self.detector.templates)}")

            self.mode = 'idle'
            self.root.attributes('-transparentcolor', 'white')

    def detection_loop(self):
        """Loop de detecção - ULTRA OTIMIZADO"""
        while self.detecting:
            try:
                loop_start = time.time()

                # Capturar tela
                screenshot = ImageGrab.grab()

                # Detectar (processamento paralelo acontece aqui)
                # Passa custom_roi se existir
                detections = self.detector.detect(screenshot, custom_roi=self.custom_roi)

                # Calcular FPS
                elapsed = time.time() - loop_start
                self.fps = 1.0 / elapsed if elapsed > 0 else 0
                self.frame_times.append(elapsed)

                # Limitar histórico de frame times
                if len(self.frame_times) > 100:
                    self.frame_times.pop(0)

                # Atualizar UI
                self.root.after(0, self.draw_detections, detections)

                # Delay otimizado
                sleep_time = max(0, DETECTION_DELAY - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                print(f"❌ Erro na detecção: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.5)

    def draw_detections(self, detections):
        """Desenha retângulos nas detecções (apenas 80%+ confiança)"""
        self.canvas.delete('detection')

        # Filtrar apenas detecções com 80%+ de confiança
        high_confidence_detections = [d for d in detections if d['confidence'] >= DISPLAY_THRESHOLD]

        # Tocar som se encontrou algo com alta confiança
        if high_confidence_detections and PLAY_SOUND_ON_DETECTION:
            try:
                # Beep curto: frequência 1000Hz, duração 100ms
                threading.Thread(target=lambda: winsound.Beep(1000, 100), daemon=True).start()
            except:
                pass  # Ignora erro se não conseguir tocar som

        for det in high_confidence_detections:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            conf = det['confidence']

            # Retângulo preenchido semi-transparente (fundo)
            # Nota: Canvas não suporta alpha em fill, então desenhamos só outline grosso

            # Retângulo externo (grosso e forte)
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline=DETECTION_COLOR, width=DETECTION_WIDTH, tags='detection'
            )

            # Retângulo interno para dar efeito de destaque
            self.canvas.create_rectangle(
                x + 2, y + 2, x + w - 2, y + h - 2,
                outline=DETECTION_COLOR, width=2, tags='detection'
            )

            # Label com confiança (mais visível)
            # Fundo do texto
            self.canvas.create_rectangle(
                x, y - 25, x + 100, y - 5,
                fill='black', outline='', tags='detection'
            )

            # Texto com confiança
            self.canvas.create_text(
                x + 5, y - 15, text=f"🌳 {conf:.0%}",
                anchor='w', font=('Arial', FONT_SIZE, 'bold'),
                fill='#FF0000', tags='detection'
            )

        # Atualizar contadores (contar só as de alta confiança)
        if high_confidence_detections:
            self.detection_count = len(high_confidence_detections)
            self.total_detections += len(high_confidence_detections)

        # Atualizar stats
        avg_fps = self._get_avg_fps()
        self.canvas.itemconfig(
            self.stats_text,
            text=f"FPS: {self.fps:.1f} (avg: {avg_fps:.1f})\n"
                 f"Detecções 80%+: {self.detection_count}\n"
                 f"Total sessão: {self.total_detections}"
        )

    def _get_avg_fps(self):
        """Calcula FPS médio"""
        if not self.frame_times:
            return 0
        avg_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_time if avg_time > 0 else 0

    def update_status(self):
        """Atualiza texto de status"""
        status_lines = []

        if self.mode == 'capturing':
            status_lines.append("🎯 MODO CAPTURA ÁRVORE")
            status_lines.append("Arraste um quadrado")
        elif self.mode == 'capturing_roi':
            status_lines.append("📐 MODO CAPTURA ROI")
            status_lines.append("Defina área de detecção")
        elif self.mode == 'detecting':
            status_lines.append("🔍 DETECTANDO...")
            status_lines.append(f"Templates: {len(self.detector.templates)}")
            if self.custom_roi:
                status_lines.append("ROI: Customizada")
        else:
            status_lines.append("⏸️ PAUSADO")
            status_lines.append(f"Templates: {len(self.detector.templates)}")
            if self.custom_roi:
                x1, y1, x2, y2 = self.custom_roi
                w, h = x2 - x1, y2 - y1
                status_lines.append(f"ROI: {w}x{h}px")

        status_lines.append("")
        status_lines.append("[-]=Árvore | [+]=Detectar | END=ROI | [*]=Sair")

        self.canvas.itemconfig(self.status_text, text="\n".join(status_lines))
        self.root.after(100, self.update_status)

    def quit(self):
        """Encerra aplicação"""
        print("\n💾 Salvando configurações...")
        self.detector.save_config()

        print(f"📊 Estatísticas finais:")
        print(f"   Total detectado: {self.total_detections}")
        print(f"   FPS médio: {self._get_avg_fps():.1f}")
        print(f"   Templates: {len(self.detector.templates)}")

        print("🧹 Limpando recursos...")
        self.detecting = False
        self.detector.cleanup()

        print("👋 Até logo!")
        self.root.quit()

    def run(self):
        """Inicia loop principal"""
        self.root.mainloop()
