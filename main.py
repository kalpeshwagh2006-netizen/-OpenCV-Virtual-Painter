import cv2
import numpy as np
import mediapipe as mp
from collections import deque
import time
import math


class VirtualPainter:
    """
    Virtual Painter with:
    - MediaPipe hand tracking
    - Freehand drawing
    - Eraser
    - Color toolbar
    - Undo / clear / save
    - Shape recognition: line, circle, triangle, rectangle, square, pentagon
    """

    def __init__(self):
        # ---------------- MediaPipe ----------------
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # ---------------- Drawing ----------------
        self.brush_color = (0, 0, 255)  # BGR
        self.last_brush_color = self.brush_color
        self.brush_thickness = 8
        self.eraser_thickness = 32
        self.eraser_mode = False
        self.shape_mode = False

        self.prev_point = None
        self.points_buffer = deque(maxlen=4)

        # Points collected during one shape gesture
        self.shape_points = []
        self.shape_preview = []

        # ---------------- Canvas ----------------
        self.canvas = None
        self.canvas_mask = None

        # ---------------- Colors ----------------
        self.colors = {
            "red": (0, 0, 255),
            "green": (0, 255, 0),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255),
            "purple": (255, 0, 255),
            "orange": (0, 165, 255),
        }
        self.color_names = list(self.colors.keys())

        # ---------------- UI ----------------
        self.buttons = []
        self.window_name = "Virtual Painter"
        self.status = "Show your hand to the camera"
        self.status_until = 0

        # ---------------- Gesture timing ----------------
        self.last_color_change = 0
        self.color_cooldown = 1.0

    # =========================================================
    # UI
    # =========================================================

    def make_buttons(self, width):
        """Create all controls inside the SAME webcam window."""
        self.buttons = []

        x = 10
        y = 10
        w = 82
        h = 52
        gap = 6

        for name in self.color_names:
            self.buttons.append({
                "name": name,
                "rect": (x, y, w, h),
                "color": self.colors[name],
            })
            x += w + gap

        for name, color, button_width in [
            ("eraser", (120, 120, 120), 88),
            ("shape", (70, 70, 180), 88),
            ("undo", (80, 80, 80), 82),
            ("clear", (60, 60, 60), 82),
            ("save", (0, 120, 0), 82),
        ]:
            self.buttons.append({
                "name": name,
                "rect": (x, y, button_width, h),
                "color": color,
            })
            x += button_width + gap

    def set_status(self, message, seconds=1.5):
        self.status = message
        self.status_until = time.time() + seconds

    def draw_toolbar(self, frame):
        """Draw the toolbar directly onto the webcam frame."""
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (0, 0),
            (frame.shape[1], 76),
            (25, 25, 25),
            -1,
        )
        frame[:] = cv2.addWeighted(overlay, 0.78, frame, 0.22, 0)

        for button in self.buttons:
            name = button["name"]
            x, y, w, h = button["rect"]
            color = button["color"]

            active = (
                (name == "eraser" and self.eraser_mode)
                or (name == "shape" and self.shape_mode)
                or (
                    name in self.colors
                    and not self.eraser_mode
                    and not self.shape_mode
                    and self.brush_color == self.colors[name]
                )
            )

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (255, 255, 255),
                3 if active else 1,
            )

            label = name.upper()
            text_size = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 2
            )[0]
            tx = x + (w - text_size[0]) // 2
            ty = y + (h + text_size[1]) // 2

            cv2.putText(
                frame,
                label,
                (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

    # =========================================================
    # Hand / gesture detection
    # =========================================================

    def fingers_up(self, hand_landmarks):
        """Return [thumb, index, middle, ring, pinky]."""
        lm = hand_landmarks.landmark
        fingers = []

        # Mirrored frame: this works for the usual front-facing webcam view.
        fingers.append(1 if lm[4].x < lm[3].x else 0)

        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            fingers.append(1 if lm[tip].y < lm[pip].y else 0)

        return fingers

    def get_index_tip(self, hand_landmarks, frame_shape):
        h, w = frame_shape[:2]
        lm = hand_landmarks.landmark[8]
        return int(lm.x * w), int(lm.y * h)

    def smooth_point(self, point):
        self.points_buffer.append(point)
        xs = [p[0] for p in self.points_buffer]
        ys = [p[1] for p in self.points_buffer]
        return int(sum(xs) / len(xs)), int(sum(ys) / len(ys))

    def handle_gesture(self, fingers):
        """
        Gesture controls:
        Index only       -> draw
        Thumb + index    -> eraser
        3 fingers        -> cycle color
        Open palm        -> clear
        Index + middle   -> shape drawing in shape mode
        """
        now = time.time()

        # Shape drawing: index + middle only.
        if self.shape_mode and fingers == [0, 1, 1, 0, 0]:
            return "shape"

        # Normal freehand drawing.
        if fingers == [0, 1, 0, 0, 0]:
            if self.eraser_mode:
                self.eraser_mode = False
                self.brush_color = self.last_brush_color
            return "draw"

        # Eraser.
        if fingers == [1, 1, 0, 0, 0]:
            if not self.eraser_mode:
                self.last_brush_color = self.brush_color
            self.eraser_mode = True
            return "erase"

        # Three fingers: cycle color.
        if sum(fingers) == 3 and now - self.last_color_change > self.color_cooldown:
            current = self.color_names.index(
                next(
                    (
                        n
                        for n, c in self.colors.items()
                        if c == self.brush_color
                    ),
                    self.color_names[0],
                )
            )
            new_index = (current + 1) % len(self.color_names)
            self.select_color(self.color_names[new_index])
            self.last_color_change = now
            return "color"

        # Open palm: clear.
        if sum(fingers) == 5:
            self.clear_canvas()
            return "clear"

        return "idle"

    # =========================================================
    # Drawing
    # =========================================================

    def draw_freehand(self, point):
        if self.prev_point is None:
            self.prev_point = point
            return

        if self.eraser_mode:
            cv2.line(
                self.canvas,
                self.prev_point,
                point,
                (0, 0, 0),
                self.eraser_thickness,
                cv2.LINE_AA,
            )
            cv2.line(
                self.canvas_mask,
                self.prev_point,
                point,
                0,
                self.eraser_thickness,
                cv2.LINE_AA,
            )
        else:
            cv2.line(
                self.canvas,
                self.prev_point,
                point,
                self.brush_color,
                self.brush_thickness,
                cv2.LINE_AA,
            )
            cv2.line(
                self.canvas_mask,
                self.prev_point,
                point,
                255,
                self.brush_thickness,
                cv2.LINE_AA,
            )

        self.prev_point = point

    def add_shape_point(self, point):
        if not self.shape_points:
            self.shape_points.append(point)
            return

        # Avoid adding nearly identical points.
        px, py = self.shape_points[-1]
        if math.hypot(point[0] - px, point[1] - py) >= 3:
            self.shape_points.append(point)

    # =========================================================
    # Shape recognition
    # =========================================================

    def recognize_shape(self, points):
        """
        Recognize the finished stroke using OpenCV contour approximation.

        Returns:
            ("line", data)
            ("triangle", data)
            ("rectangle", data)
            ("square", data)
            ("pentagon", data)
            ("circle", data)
            ("freeform", data)
        """
        if len(points) < 12:
            return "freeform", None

        pts = np.array(points, dtype=np.int32)

        # Remove tiny jitter.
        epsilon_smooth = max(1.0, 0.01 * cv2.arcLength(pts.reshape(-1, 1, 2), False))
        approx_curve = cv2.approxPolyDP(
            pts.reshape(-1, 1, 2),
            epsilon_smooth,
            False,
        ).reshape(-1, 2)

        # Determine whether the endpoints are close enough to close the shape.
        start = tuple(pts[0])
        end = tuple(pts[-1])
        end_distance = math.hypot(end[0] - start[0], end[1] - start[1])

        x, y, w, h = cv2.boundingRect(pts.reshape(-1, 1, 2))
        diagonal = max(math.hypot(w, h), 1.0)

        # A single straight stroke.
        if len(points) >= 10:
            vx, vy, x0, y0 = cv2.fitLine(
                pts.astype(np.float32),
                cv2.DIST_L2,
                0,
                0.01,
                0.01,
            )
            vx, vy = float(vx), float(vy)

            distances = np.abs(
                vy * (pts[:, 0] - float(x0))
                - vx * (pts[:, 1] - float(y0))
            )
            line_error = float(np.mean(distances))

            if line_error < max(8.0, diagonal * 0.04):
                return "line", pts

        # A circle is usually closed and has high circularity.
        contour = pts.reshape(-1, 1, 2)
        perimeter = cv2.arcLength(contour, True)
        area = cv2.contourArea(contour)

        if perimeter > 0 and area > 0 and end_distance < diagonal * 0.25:
            circularity = 4 * math.pi * area / (perimeter * perimeter)

            # Compare width/height too, to reject very elongated shapes.
            aspect = w / max(h, 1)

            if circularity > 0.72 and 0.72 < aspect < 1.28:
                center, radius = cv2.minEnclosingCircle(contour)
                return "circle", (
                    (int(center[0]), int(center[1])),
                    max(2, int(radius)),
                )

        # For polygon recognition, explicitly close the stroke.
        closed_pts = pts.copy()
        if end_distance > diagonal * 0.15:
            closed_pts = np.vstack([closed_pts, closed_pts[0]])

        contour = closed_pts.reshape(-1, 1, 2)
        perimeter = cv2.arcLength(contour, True)

        if perimeter <= 0:
            return "freeform", None

        approx = cv2.approxPolyDP(
            contour,
            0.035 * perimeter,
            True,
        )

        vertices = len(approx)

        if vertices == 3:
            return "triangle", approx.reshape(-1, 2)

        if vertices == 4:
            bx, by, bw, bh = cv2.boundingRect(approx)
            aspect = bw / max(bh, 1)

            # Square if width and height are close.
            if 0.80 <= aspect <= 1.25:
                return "square", approx.reshape(-1, 2)
            return "rectangle", approx.reshape(-1, 2)

        if vertices == 5:
            return "pentagon", approx.reshape(-1, 2)

        return "freeform", pts

    def draw_recognized_shape(self, shape_name, data):
        if shape_name == "line":
            pts = data
            cv2.polylines(
                self.canvas,
                [pts.reshape(-1, 1, 2)],
                False,
                self.brush_color,
                self.brush_thickness,
                cv2.LINE_AA,
            )
            cv2.polylines(
                self.canvas_mask,
                [pts.reshape(-1, 1, 2)],
                False,
                255,
                self.brush_thickness,
                cv2.LINE_AA,
            )

        elif shape_name == "circle":
            center, radius = data
            cv2.circle(
                self.canvas,
                center,
                radius,
                self.brush_color,
                self.brush_thickness,
                cv2.LINE_AA,
            )
            cv2.circle(
                self.canvas_mask,
                center,
                radius,
                255,
                self.brush_thickness,
                cv2.LINE_AA,
            )

        else:
            pts = np.array(data, dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(
                self.canvas,
                [pts],
                True,
                self.brush_color,
                self.brush_thickness,
                cv2.LINE_AA,
            )
            cv2.polylines(
                self.canvas_mask,
                [pts],
                True,
                255,
                self.brush_thickness,
                cv2.LINE_AA,
            )

    def finish_shape(self):
        if len(self.shape_points) < 12:
            self.shape_points.clear()
            self.shape_preview.clear()
            return

        shape_name, data = self.recognize_shape(self.shape_points)

        if shape_name != "freeform":
            self.draw_recognized_shape(shape_name, data)
            self.set_status(f"Detected: {shape_name.upper()}", 1.8)
        else:
            # If not recognized, keep the original stroke instead of losing it.
            pts = np.array(self.shape_points, dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(
                self.canvas,
                [pts],
                False,
                self.brush_color,
                self.brush_thickness,
                cv2.LINE_AA,
            )
            cv2.polylines(
                self.canvas_mask,
                [pts],
                False,
                255,
                self.brush_thickness,
                cv2.LINE_AA,
            )
            self.set_status("Freeform stroke", 1.2)

        self.shape_points.clear()
        self.shape_preview.clear()

    def draw_shape_preview(self, frame):
        if len(self.shape_points) < 2:
            return

        pts = np.array(self.shape_points, dtype=np.int32).reshape(-1, 1, 2)

        # Show the user's raw stroke while they are drawing.
        cv2.polylines(
            frame,
            [pts],
            False,
            self.brush_color,
            3,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            "Release fingers to recognize shape",
            (15, 105),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

    # =========================================================
    # Canvas actions
    # =========================================================

    def clear_canvas(self):
        if self.canvas is not None:
            self.canvas[:] = 0
            self.canvas_mask[:] = 0
            self.prev_point = None
            self.points_buffer.clear()
            self.shape_points.clear()
            self.set_status("Canvas cleared")

    def save_canvas(self):
        if self.canvas is None:
            return

        # White background image containing only the drawing.
        result = np.ones_like(self.canvas) * 255
        result[self.canvas_mask > 0] = self.canvas[self.canvas_mask > 0]

        filename = f"virtual_painter_{int(time.time())}.png"
        cv2.imwrite(filename, result)
        self.set_status(f"Saved: {filename}", 2.5)
        print(f"Canvas saved as {filename}")

    def select_color(self, name):
        if name in self.colors:
            self.brush_color = self.colors[name]
            self.last_brush_color = self.brush_color
            self.eraser_mode = False
            self.set_status(f"Brush: {name.upper()}")

    def toggle_shape_mode(self):
        self.shape_mode = not self.shape_mode
        self.eraser_mode = False
        self.prev_point = None
        self.points_buffer.clear()
        self.shape_points.clear()

        if self.shape_mode:
            self.set_status("SHAPE MODE: Index + Middle finger")
        else:
            self.set_status("BRUSH MODE")

    # =========================================================
    # Mouse
    # =========================================================

    def handle_button_click(self, x, y):
        for button in self.buttons:
            bx, by, bw, bh = button["rect"]

            if bx <= x <= bx + bw and by <= y <= by + bh:
                name = button["name"]

                if name in self.colors:
                    self.select_color(name)

                elif name == "eraser":
                    self.eraser_mode = True
                    self.shape_mode = False
                    self.set_status("ERASER")

                elif name == "shape":
                    self.toggle_shape_mode()

                elif name == "undo":
                    # Lightweight undo is implemented through the last saved
                    # canvas snapshot below.
                    self.undo()

                elif name == "clear":
                    self.clear_canvas()

                elif name == "save":
                    self.save_canvas()

                return True

        return False

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.handle_button_click(x, y)

    # =========================================================
    # Simple undo
    # =========================================================

    def save_undo_state(self):
        if self.canvas is not None:
            self.undo_canvas = self.canvas.copy()
            self.undo_mask = self.canvas_mask.copy()

    def undo(self):
        if hasattr(self, "undo_canvas"):
            self.canvas = self.undo_canvas.copy()
            self.canvas_mask = self.undo_mask.copy()
            self.set_status("Undo")
        else:
            self.set_status("Nothing to undo")

    # =========================================================
    # Main loop
    # =========================================================

    def run(self):
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("ERROR: Could not open webcam.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        while True:
            ret, frame = cap.read()

            if not ret:
                print("ERROR: Could not read webcam frame.")
                break

            frame = cv2.flip(frame, 1)

            if self.canvas is None:
                self.canvas = np.zeros_like(frame)
                self.canvas_mask = np.zeros(
                    frame.shape[:2],
                    dtype=np.uint8,
                )
                self.make_buttons(frame.shape[1])

            # MediaPipe processing.
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)

            gesture = "idle"

            if results.multi_hand_landmarks:
                hand = results.multi_hand_landmarks[0]

                # Draw all 21 landmarks.
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(
                        color=(0, 255, 0),
                        thickness=2,
                        circle_radius=4,
                    ),
                    self.mp_drawing.DrawingSpec(
                        color=(255, 0, 0),
                        thickness=2,
                    ),
                )

                fingers = self.fingers_up(hand)
                gesture = self.handle_gesture(fingers)
                index_tip = self.get_index_tip(hand, frame.shape)

                cv2.circle(
                    frame,
                    index_tip,
                    10,
                    (0, 255, 255),
                    -1,
                )
                cv2.circle(
                    frame,
                    index_tip,
                    13,
                    (255, 255, 255),
                    2,
                )

                if self.shape_mode:
                    # Shape mode uses index + middle finger together.
                    if gesture == "shape":
                        point = self.smooth_point(index_tip)
                        self.add_shape_point(point)
                    else:
                        # Finishing gesture: fingers separate.
                        if self.shape_points:
                            self.finish_shape()

                        self.prev_point = None
                        self.points_buffer.clear()

                else:
                    # Normal freehand / eraser mode.
                    if gesture in ("draw", "erase"):
                        if gesture == "draw":
                            self.save_undo_state()

                        point = self.smooth_point(index_tip)
                        self.draw_freehand(point)
                    else:
                        self.prev_point = None
                        self.points_buffer.clear()

            else:
                if self.shape_mode and self.shape_points:
                    self.finish_shape()

                self.prev_point = None
                self.points_buffer.clear()

            # Draw the current shape stroke as a preview, not onto the canvas yet.
            if self.shape_mode:
                self.draw_shape_preview(frame)

            # Blend only the pixels where the canvas contains drawing.
            if np.any(self.canvas_mask):
                blended = cv2.addWeighted(
                    frame,
                    0.45,
                    self.canvas,
                    0.55,
                    0,
                )
                mask = self.canvas_mask > 0
                frame[mask] = blended[mask]

            # Toolbar.
            self.draw_toolbar(frame)

            # Status.
            if self.shape_mode:
                mode = "SHAPE"
            elif self.eraser_mode:
                mode = "ERASER"
            else:
                mode = "BRUSH"

            color_name = next(
                (
                    n.upper()
                    for n, c in self.colors.items()
                    if c == self.brush_color
                ),
                "CUSTOM",
            )

            cv2.putText(
                frame,
                f"MODE: {mode}   COLOR: {color_name}",
                (15, frame.shape[0] - 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (
                    (255, 255, 255)
                    if self.eraser_mode or self.shape_mode
                    else self.brush_color
                ),
                2,
                cv2.LINE_AA,
            )

            help_text = (
                "Shape: click SHAPE, then Index+Middle draw | "
                "Release = recognize | Q = Quit"
            )

            cv2.putText(
                frame,
                help_text,
                (15, frame.shape[0] - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.46,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

            if time.time() < self.status_until:
                cv2.putText(
                    frame,
                    self.status,
                    (frame.shape[1] - 390, frame.shape[0] - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow(self.window_name, frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            elif key == ord("c"):
                self.clear_canvas()

            elif key == ord("s"):
                self.save_canvas()

            elif key == ord("h"):
                self.toggle_shape_mode()

        cap.release()
        cv2.destroyAllWindows()
        self.hands.close()


if __name__ == "__main__":
    painter = VirtualPainter()
    painter.run()
