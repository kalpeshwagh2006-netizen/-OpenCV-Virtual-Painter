import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog
from PIL import Image, ImageTk
import threading
import time
import mediapipe as mp
from collections import deque

class python :
    def __init__(self):
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # Drawing parameters
        self.brush_color = (0, 0, 255)  # Default red (BGR format)
        self.last_brush_color = self.brush_color
        self.brush_thickness = 8
        self.eraser_mode = False
        self.drawing = False
        self.prev_point = None
        
        # Smoothing
        self.points_buffer = deque(maxlen=5)
        
        # Clear confirmation
        self.clear_requested = False
        
        # Canvas for drawing
        self.canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Setup GUI
        self.root = tk.Tk()
        self.root.title("Virtual Painter - Finger Drawing")
        self.root.geometry("1000x700")
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
        self.status_label = ttk.Label(main_frame, text="Mode: BRUSH | Use index finger to draw")
        self.status_label.grid(row=2, column=0, columnspan=4, pady=10)
        
        # Instructions label
        instructions = ttk.Label(main_frame, 
                               text="Controls: Buttons for colors/eraser | Drawing: Index finger gesture",
                               font=("Arial", 10))
        instructions.grid(row=3, column=0, columnspan=4, pady=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
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
        if self.eraser_mode:
            self.last_brush_color = self.brush_color
        else:
            self.brush_color = self.last_brush_color
        self.update_status()
        
    def clear_canvas(self):
        if self.clear_requested:
            self.canvas = np.zeros((480, 640, 3), dtype=np.uint8)
            self.clear_requested = False
            # Show confirmation message
            cv2.putText(self.frame, "Canvas Cleared!", 
                       (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
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
            self.status_label.config(text=f"Mode: {mode} | {color_name} | Use index finger to draw")
        else:
            self.status_label.config(text=f"Mode: {mode} | Use index finger to erase")
            
    def fingers_up(self, hand_landmarks):
        """Detect which fingers are up"""
        fingers = []
        
        # Finger tip landmarks (8, 12, 16, 20) and corresponding pip joints (6, 10, 14, 18)
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        
        # Thumb (special case - compare x coordinates)
        if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
            fingers.append(1)
        else:
            fingers.append(0)
        
        # Four fingers (compare y coordinates)
        for tip, pip in zip(finger_tips, finger_pips):
            if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y:
                fingers.append(1)
            else:
                fingers.append(0)
        
        return fingers
    
    def get_finger_tip(self, hand_landmarks, finger_index):
        """Get coordinates of finger tip"""
        h, w = 480, 640  # Fixed canvas size
        finger_tip_landmarks = [8, 12, 16, 20]  # index, middle, ring, pinky
        landmark = hand_landmarks.landmark[finger_tip_landmarks[finger_index]]
        return int(landmark.x * w), int(landmark.y * h)
    
    def smooth_point(self, current_point):
        """Simple smoothing using linear interpolation"""
        if self.prev_point is None:
            self.prev_point = current_point
            return current_point
        
        # Simple linear interpolation for smoother movement
        smoothed_x = int((self.prev_point[0] + current_point[0]) / 2)
        smoothed_y = int((self.prev_point[1] + current_point[1]) / 2)
        
        smoothed_point = (smoothed_x, smoothed_y)
        self.prev_point = smoothed_point
        return smoothed_point
    
    def draw_on_canvas(self, point):
        """Draw on the canvas with simple line connections"""
        if self.prev_point is None:
            return
            
        # Draw line between previous and current point
        if self.eraser_mode:
            cv2.line(self.canvas, self.prev_point, point, (0, 0, 0), self.brush_thickness * 3)
        else:
            cv2.line(self.canvas, self.prev_point, point, self.brush_color, self.brush_thickness)
        
        # Always update previous point for continuous drawing
        self.prev_point = point
            
    def handle_gestures(self, hand_landmarks, fingers):
        """Handle all gesture controls"""
        # Thumb + Index finger gesture for eraser mode
        if fingers[0] == 1 and fingers[1] == 1 and sum(fingers[2:]) == 0:  # Thumb + Index finger up, others down
            if not self.eraser_mode:
                self.last_brush_color = self.brush_color
            self.eraser_mode = True
            # Visual feedback for eraser mode
            cv2.putText(self.frame, "Eraser Mode", 
                       (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
            cv2.circle(self.frame, (50, 190), 20, (150, 150, 150), -1)
            cv2.circle(self.frame, (50, 190), 22, (255, 255, 255), 2)
            return True
        
        # Only Index finger gesture for brush mode
        if fingers[0] == 0 and fingers[1] == 1 and sum(fingers[2:]) == 0:  # Only Index finger up
            if self.eraser_mode:
                self.eraser_mode = False
                self.brush_color = self.last_brush_color
                # Visual feedback for brush mode
                cv2.putText(self.frame, "Brush Mode", 
                           (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.brush_color, 2)
                cv2.circle(self.frame, (50, 190), 20, self.brush_color, -1)
                cv2.circle(self.frame, (50, 190), 22, (255, 255, 255), 2)
            return True
        
        # Three-finger gesture for color cycling
        if sum(fingers) == 3:  # Any 3 fingers up
            # Color cycling logic - cycle through colors
            colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255), (0, 165, 255)]
            if not self.eraser_mode:
                current_index = colors.index(self.brush_color) if self.brush_color in colors else 0
                next_index = (current_index + 1) % len(colors)
                self.brush_color = colors[next_index]
                self.last_brush_color = self.brush_color
                
                # Enhanced visual feedback
                color_names = ["RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "ORANGE"]
                cv2.putText(self.frame, f"Color: {color_names[next_index]}", 
                           (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.brush_color, 2)
                cv2.circle(self.frame, (50, 190), 20, self.brush_color, -1)
                cv2.circle(self.frame, (50, 190), 22, (255, 255, 255), 2)
                
                return True
        
        # Palm gesture for clear confirmation (all fingers up)
        if sum(fingers) == 5:
            self.clear_requested = True
            return True
            
        return False

    def update_video(self):
        while self.running:
            ret, self.frame = self.cap.read()
            if ret:
                # Flip frame horizontally for mirror effect
                self.frame = cv2.flip(self.frame, 1)
                
                # Resize frame to match canvas size
                self.frame = cv2.resize(self.frame, (640, 480))
                
                # Initialize canvas if not exists
                if self.canvas is None:
                    self.canvas = np.zeros_like(self.frame)
                
                # Convert BGR to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_frame)
                
                # Process hand landmarks for drawing and gestures
                if results.multi_hand_landmarks:
                    hand_landmarks = results.multi_hand_landmarks[0]
                    
                    # Draw hand landmarks for visualization
                    self.mp_drawing.draw_landmarks(
                        self.frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                        self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
                    
                    # Get finger states
                    fingers = self.fingers_up(hand_landmarks)
                    
                    # Handle all gestures
                    self.handle_gestures(hand_landmarks, fingers)
                    
                    # Get index finger tip
                    index_tip = self.get_finger_tip(hand_landmarks, 0)  # 0 = index finger
                    
                    # Visualize finger tip
                    cv2.circle(self.frame, index_tip, 10, (0, 255, 255), -1)
                    
                    # Drawing logic - only index finger up
                    if fingers[1] == 1 and sum(fingers[2:]) == 0:  # Only index finger up
                        smoothed_point = self.smooth_point(index_tip)
                        self.draw_on_canvas(smoothed_point)
                        self.drawing = True
                    else:
                        self.prev_point = None
                        self.drawing = False
                
                # Combine canvas with frame using alpha blending
                alpha = 0.7
                combined = cv2.addWeighted(self.frame, 1 - alpha, self.canvas, alpha, 0)
                
                # Display current mode and color on the frame
                mode = "ERASER" if self.eraser_mode else "BRUSH"
                cv2.putText(combined, f"Mode: {mode}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                if not self.eraser_mode:
                    color_names = {
                        (0, 0, 255): "RED",
                        (0, 255, 0): "GREEN", 
                        (255, 0, 0): "BLUE",
                        (0, 255, 255): "YELLOW",
                        (255, 0, 255): "PURPLE",
                        (0, 165, 255): "ORANGE"
                    }
                    color_name = color_names.get(tuple(self.brush_color), "CUSTOM")
                    cv2.putText(combined, f"Color: {color_name}", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.brush_color, 2)
                
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
            cv2.destroyAllWindows()
            
if __name__ == "__main__":
    app = VirtualPainterCombined()
    app.run()
