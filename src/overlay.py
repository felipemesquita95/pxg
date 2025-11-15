"""
Interface overlay transparente para captura e visualização
"""

import tkinter as tk
from tkinter import Canvas
from PIL import ImageGrab
import keyboard
import threading
import time
from src.config import *


class OverlayWindow:
    """Janela transparente overlay - VERSÃO OTIMIZADA"""

    def __init__(self, detector):
        self.detector = detector

        self.mode = 'idle'
        self.capturing = False
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None

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
        print(f"NUMPAD [*] - SAIR")
        print(f"📚 Templates: {len(self.detector.templates)}")
        print(f"⚡ FPS Target: {FPS_TARGET}")
        print(f"🎯 ROI: {'ATIVO' if USE_ROI else 'DESATIVADO'}")
        print(f"🚀 Threading: {'ATIVO' if USE_THREADING else 'DESATIVADO'}")
        print("="*60 + "\n")

    def setup_hotkeys(self):
        """Configura atalhos de teclado"""
        keyboard.add_hotkey(HOTKEY_CAPTURE, self.toggle_capture_mode)
        keyboard.add_hotkey(HOTKEY_DETECT, self.toggle_detection_mode)
        keyboard.add_hotkey(HOTKEY_QUIT, self.quit)

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
        """Desenha indicador visual da ROI"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        pad_w = int(screen_width * ROI_PADDING)
        pad_h = int(screen_height * ROI_PADDING)

        x1 = pad_w
        y1 = pad_h
        x2 = screen_width - pad_w
        y2 = screen_height - pad_h

        self.roi_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline='cyan', width=2, dash=(5, 5), tags='roi'
        )

        # Texto explicativo
        self.canvas.create_text(
            screen_width // 2, y1 - 20,
            text="🎯 ÁREA DE DETECÇÃO (ROI)",
            font=('Arial', 12, 'bold'),
            fill='cyan', tags='roi'
        )

    def on_click(self, event):
        """Mouse click - inicia captura"""
        if self.mode != 'capturing':
            return
        self.capturing = True
        self.start_x = event.x
        self.start_y = event.y
        if self.current_rect:
            self.canvas.delete(self.current_rect)

    def on_drag(self, event):
        """Mouse drag - desenha retângulo"""
        if not self.capturing:
            return
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline=CAPTURE_COLOR, width=CAPTURE_WIDTH
        )

    def on_release(self, event):
        """Mouse release - captura template"""
        if not self.capturing:
            return
        self.capturing = False

        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        width = x2 - x1
        height = y2 - y1

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
                detections = self.detector.detect(screenshot)

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
        """Desenha retângulos nas detecções"""
        self.canvas.delete('detection')

        for det in detections:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            conf = det['confidence']

            # Retângulo
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline=DETECTION_COLOR, width=DETECTION_WIDTH, tags='detection'
            )

            # Label com confiança
            self.canvas.create_text(
                x, y - 10, text=f"🌳 {conf:.0%}",
                anchor='sw', font=('Arial', FONT_SIZE, 'bold'),
                fill=DETECTION_COLOR, tags='detection'
            )

        # Atualizar contadores
        if detections:
            self.detection_count = len(detections)
            self.total_detections += len(detections)

        # Atualizar stats
        avg_fps = self._get_avg_fps()
        self.canvas.itemconfig(
            self.stats_text,
            text=f"FPS: {self.fps:.1f} (avg: {avg_fps:.1f})\n"
                 f"Detecções agora: {self.detection_count}\n"
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
