import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog
from PIL import Image, ImageTk
import threading
import time

class VirtualPainterGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Virtual Painter")
        self.root.geometry("1000x700")
        
        # Drawing parameters
        self.brush_color = (0, 0, 255)  # Default red (BGR format)
        self.brush_thickness = 8
        self.eraser_mode = False
        self.drawing = False
        self.prev_point = None
        
        # Canvas for drawing
        self.canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Setup GUI
        self.setup_gui()
        
        # Start video capture
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Start video thread
        self.running = True
        self.video_thread = threading.Thread(target=self.update_video)
        self.video_thread.daemon = True
        self.video_thread.start()
        
    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Video frame
        self.video_label = ttk.Label(main_frame)
        self.video_label.grid(row=0, column=0, columnspan=4, pady=10)
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        # Color buttons
        colors = [
            ("Red", (0, 0, 255)),
            ("Green", (0, 255, 0)),
            ("Blue", (255, 0, 0)),
            ("Yellow", (0, 255, 255)),
            ("Purple", (255, 0, 255)),
            ("Orange", (0, 165, 255))
        ]
        
        for i, (name, color) in enumerate(colors):
            btn = ttk.Button(control_frame, text=name, 
                           command=lambda c=color: self.set_brush_color(c))
            btn.grid(row=0, column=i, padx=5)
        
        # Custom color button
        custom_btn = ttk.Button(control_frame, text="Custom Color", 
                              command=self.choose_custom_color)
        custom_btn.grid(row=0, column=6, padx=5)
        
        # Eraser button
        self.eraser_btn = ttk.Button(control_frame, text="Eraser", 
                                   command=self.toggle_eraser)
        self.eraser_btn.grid(row=0, column=7, padx=5)
        
        # Clear button
        clear_btn = ttk.Button(control_frame, text="Clear Canvas", 
                             command=self.clear_canvas)
        clear_btn.grid(row=0, column=8, padx=5)
        
        # Save button
        save_btn = ttk.Button(control_frame, text="Save", 
                            command=self.save_canvas)
        save_btn.grid(row=0, column=9, padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Mode: BRUSH | Click and drag to draw")
        self.status_label.grid(row=2, column=0, columnspan=4, pady=10)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Bind mouse events
        self.video_label.bind("<Button-1>", self.on_mouse_down)
        self.video_label.bind("<B1-Motion>", self.on_mouse_drag)
        self.video_label.bind("<ButtonRelease-1>", self.on_mouse_up)
        
    def set_brush_color(self, color):
        self.brush_color = color
        self.eraser_mode = False
        self.update_status()
        
    def choose_custom_color(self):
        color = colorchooser.askcolor(title="Choose brush color")
        if color[0]:
            self.brush_color = tuple(int(c) for c in color[0])
            self.eraser_mode = False
            self.update_status()
            
    def toggle_eraser(self):
        self.eraser_mode = not self.eraser_mode
        self.update_status()
        
    def clear_canvas(self):
        self.canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        
    def save_canvas(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filename:
            cv2.imwrite(filename, self.canvas)
            
    def update_status(self):
        mode = "ERASER" if self.eraser_mode else "BRUSH"
        if not self.eraser_mode:
            color_name = f"Color: RGB{self.brush_color[::-1]}"  # Convert BGR to RGB for display
            self.status_label.config(text=f"Mode: {mode} | {color_name} | Click and drag to draw")
        else:
            self.status_label.config(text=f"Mode: {mode} | Click and drag to erase")
            
    def on_mouse_down(self, event):
        self.drawing = True
        self.prev_point = (event.x, event.y)
        
    def on_mouse_drag(self, event):
        if self.drawing and self.prev_point:
            current_point = (event.x, event.y)
            self.draw_on_canvas(self.prev_point, current_point)
            self.prev_point = current_point
            
    def on_mouse_up(self, event):
        self.drawing = False
        self.prev_point = None
        
    def draw_on_canvas(self, start_point, end_point):
        if self.eraser_mode:
            cv2.line(self.canvas, start_point, end_point, (0, 0, 0), self.brush_thickness * 3)
        else:
            cv2.line(self.canvas, start_point, end_point, self.brush_color, self.brush_thickness)
            
    def update_video(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Combine canvas with frame
                combined = cv2.addWeighted(frame, 0.7, self.canvas, 0.3, 0)
                
                # Convert to PIL Image
                combined_rgb = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(combined_rgb)
                
                # Convert to Tkinter PhotoImage
                photo = ImageTk.PhotoImage(image=pil_image)
                
                # Update label
                self.video_label.config(image=photo)
                self.video_label.image = photo
                
            time.sleep(0.03)  # ~30 FPS
            
    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.running = False
            self.cap.release()
            
if __name__ == "__main__":
    app = VirtualPainterGUI()
    app.run()
