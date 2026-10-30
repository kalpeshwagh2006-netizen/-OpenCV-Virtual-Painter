import cv2
import numpy as np
import mediapipe as mp

# Initialize MediaPipe hand detector
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Setup webcam
cap = cv2.VideoCapture(0)
cap.set(3, 1280)  # width
cap.set(4, 720)   # height

# Create a white canvas for drawing
canvas = np.zeros((720, 1280, 3), dtype=np.uint8)

# Colors
colors = [(255, 0, 255), (0, 255, 0), (255, 255, 0), (0, 0, 255)]
color_index = 0
draw_color = colors[color_index]
eraser_on = False

# Store previous point
prev_x, prev_y = 0, 0

def fingers_up(hand_landmarks):
    tips = [8, 12, 16, 20]
    fingers = []
    for tip in tips:
        finger_up = hand_landmarks.landmark[tip].y < hand_landmarks.landmark[tip - 2].y
        fingers.append(finger_up)
    return fingers

while True:
    success, frame = cap.read()
    if not success:
        print("Failed to capture frame from webcam. Exiting...")
        break
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            lm = hand_landmarks.landmark

            index_x = int(lm[8].x * 1280)
            index_y = int(lm[8].y * 720)
            middle_x = int(lm[12].x * 1280)
            middle_y = int(lm[12].y * 720)

            fingers = fingers_up(hand_landmarks)

            # Selection Mode: Both Index and Middle fingers up
            if fingers[0] and fingers[1]:
                prev_x, prev_y = 0, 0  # reset
                if index_y < 100:
                    # Top selection area
                    if 100 < index_x < 200:
                        color_index = 0
                    elif 250 < index_x < 350:
                        color_index = 1
                    elif 400 < index_x < 500:
                        color_index = 2
                    elif 550 < index_x < 650:
                        color_index = 3
                    elif 700 < index_x < 800:
                        eraser_on = not eraser_on
                draw_color = (0, 0, 0) if eraser_on else colors[color_index]
                cv2.rectangle(frame, (index_x - 20, index_y - 20), (middle_x + 20, middle_y + 20), draw_color, cv2.FILLED)

            # Drawing Mode: Only Index finger up
            elif fingers[0] and not fingers[1]:
                cv2.circle(frame, (index_x, index_y), 10, draw_color, cv2.FILLED)
                if prev_x == 0 and prev_y == 0:
                    prev_x, prev_y = index_x, index_y
                if eraser_on:
                    cv2.line(canvas, (prev_x, prev_y), (index_x, index_y), (0, 0, 0), 50)
                else:
                    cv2.line(canvas, (prev_x, prev_y), (index_x, index_y), draw_color, 15)
                prev_x, prev_y = index_x, index_y

            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # Combine frame and canvas
    gray_canvas = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray_canvas, 50, 255, cv2.THRESH_BINARY_INV)
    mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    frame = cv2.bitwise_and(frame, mask)
    frame = cv2.bitwise_or(frame, canvas)

    # Draw color palette
    cv2.rectangle(frame, (100, 0), (200, 100), colors[0], cv2.FILLED)
    cv2.rectangle(frame, (250, 0), (350, 100), colors[1], cv2.FILLED)
    cv2.rectangle(frame, (400, 0), (500, 100), colors[2], cv2.FILLED)
    cv2.rectangle(frame, (550, 0), (650, 100), colors[3], cv2.FILLED)
    cv2.rectangle(frame, (700, 0), (800, 100), (0, 0, 0), 2)
    cv2.putText(frame, 'Eraser', (710, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)

    # Show frame
    cv2.imshow("Virtual Painter", frame)
    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    elif key == ord('c'):
        canvas[:] = 0  # Clear canvas

cap.release()
cv2.destroyAllWindows()