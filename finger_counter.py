import cv2
import numpy as np
from sklearn.metrics import pairwise
import random

background = None
accumulated_weight = 0.5

# Filming area.
roi_top = 20
roi_bottom = 300
roi_right = 300
roi_left = 600


# Calculates the average background color.
def calculate_accumulated_weight(frame, accumulated_weight):
    global background

    if background is None:
        background = frame.copy().astype("float")
        return None
    cv2.accumulateWeighted(frame, background, accumulated_weight)


def segment(frame, threshold=25):
    global background

    diff = cv2.absdiff(background.astype("uint8"), frame)
    _, thresholded = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

    contours, hierarchy = cv2.findContours(thresholded.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        return None
    else:
        hand_segment = max(contours, key=cv2.contourArea)
        return (thresholded, hand_segment)


# Counts the number of fingers using convex hull.
# It finds the center of your hand and top points of the fingers.
def count_fingers(thresholded, hand_segment):
    convex_hull = cv2.convexHull(hand_segment)

    top = tuple(convex_hull[convex_hull[:, :, 1].argmin()][0])
    bottom = tuple(convex_hull[convex_hull[:, :, 1].argmax()][0])
    left = tuple(convex_hull[convex_hull[:, :, 0].argmin()][0])
    right = tuple(convex_hull[convex_hull[:, :, 0].argmax()][0])

    # Center of the hand.
    center_x = (left[0] + right[0]) // 2
    center_y = (top[1] + bottom[1]) // 2

    distance = pairwise.euclidean_distances([(center_x, center_y)], Y=[left, right, top, bottom])[0]
    max_distance = distance.max()

    # You can play the 0.8 according you hand size.
    radius = int(0.8 * max_distance)
    circumference = (2 * np.pi * radius)

    circular_roi = np.zeros(thresholded.shape[:2], dtype="uint8")
    cv2.circle(circular_roi, (center_x, center_y), radius, 255, 10)

    circular_roi = cv2.bitwise_and(thresholded, thresholded, mask=circular_roi)

    contours, hierarchy = cv2.findContours(circular_roi.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    count = 0
    finger_coordinates = []
    for cnt in contours:
        (x, y, w, h) = cv2.boundingRect(cnt)

        out_of_wrist = ((center_y + (center_y * 0.25)) > (y + h))
        limit_points = ((circumference * 0.25) > cnt.shape[0])

        if out_of_wrist and limit_points:
            finger_coordinates.append((x, y))
            count += 1

    return [count, (center_x, center_y), finger_coordinates]


cam = cv2.VideoCapture(0)
num_frames = 0

while True:
    ret, frame = cam.read()
    frame = cv2.flip(frame, 1)

    frame_copy = frame.copy()
    roi = frame[roi_top:roi_bottom, roi_right:roi_left]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 0)

    if num_frames < 60:
        calculate_accumulated_weight(gray, accumulated_weight)
        if num_frames <= 59:
            cv2.imshow("Finger Count", frame_copy)

    else:
        hand = segment(gray)

        if hand is not None:
            thresholded, hand_segment = hand

            cv2.drawContours(frame_copy, [hand_segment + (roi_right, roi_top)], -1, (255, 0, 0), 1)
            fingers = count_fingers(thresholded, hand_segment)
            center_of_hand = fingers[1]
            fingers_top_point = fingers[2]

            for (x, y) in fingers_top_point:
                # Draw lines between center of the hand and top points of the fingers.
                cv2.line(frame_copy, center_of_hand, (x, y), (255, 255, 0), 5)
                # Top points of the fingers in different colors.
                cv2.circle(frame_copy, (x, y), 5, (random.randint(0, 256),
                                                   random.randint(0, 256), random.randint(0, 256)), -1)

            cv2.circle(frame_copy, center_of_hand, 5, (0, 0, 255), -1)
            cv2.putText(frame_copy, str(fingers[0]), (70, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow("Thesholded", thresholded)

        cv2.rectangle(frame_copy, (roi_left, roi_top), (roi_right, roi_bottom), (0, 0, 255), 5)

    num_frames += 1
    cv2.imshow("Finger Count", frame_copy)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()