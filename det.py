import cv2
import mediapipe as mp

def main():
    # Initialize video capture
    cap = cv2.VideoCapture(0)

    # Initialize Mediapipe Face and Hands modules
    mp_face = mp.solutions.face_detection
    mp_hands = mp.solutions.hands
    face_detection = mp_face.FaceDetection(min_detection_confidence=0.2)
    hand_tracking = mp_hands.Hands(min_detection_confidence=0.2, min_tracking_confidence=0.2)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        results_face = face_detection.process(rgb_frame)
        if results_face.detections:
            for detection in results_face.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                bbox = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                       int(bboxC.width * iw), int(bboxC.height * ih)
                cv2.rectangle(frame, bbox, (0, 255, 0), 2)

        # Detect hands
        results_hands = hand_tracking.process(rgb_frame)
        if results_hands.multi_hand_landmarks:
            for hand_landmarks in results_hands.multi_hand_landmarks:
                # Draw hand landmarks
                mp.solutions.drawing_utils.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Display the output
        cv2.imshow('Face and Hand Detection', frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture and close all windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
