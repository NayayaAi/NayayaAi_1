# Face recognition helper module for missing person identification
# Gracefully handles missing face_recognition library

import os

FACE_RECOGNITION_AVAILABLE = False

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    print("face_recognition library loaded successfully.")
except Exception as e:
    FACE_RECOGNITION_AVAILABLE = False
    print("WARNING: face_recognition library not available. Running in DEMO mode.")
    print("Install with: pip install face-recognition dlib")
    print(f"Error: {e}")


def compare_faces(image_path1, image_path2, tolerance=0.6):
    """
    Compare two face images and return a match result dict.
    Falls back to a demo result if the library is unavailable.

    Returns:
        {
            'is_match': bool,
            'confidence_score': float (0.0 - 1.0),
            'distance': float,
            'details': str
        }
    """
    if not FACE_RECOGNITION_AVAILABLE:
        # Demo mode: simulate a moderate result so the app stays functional
        return {
            'is_match': False,
            'confidence_score': 0.5,
            'distance': 0.5,
            'details': 'Demo mode — face_recognition library not installed. Install it for real matching.'
        }

    try:
        img1 = face_recognition.load_image_file(image_path1)
        img2 = face_recognition.load_image_file(image_path2)

        enc1 = face_recognition.face_encodings(img1)
        enc2 = face_recognition.face_encodings(img2)

        if not enc1:
            return {
                'is_match': False,
                'confidence_score': 0.0,
                'distance': 1.0,
                'details': 'No face detected in the reference (police) photo.'
            }

        if not enc2:
            return {
                'is_match': False,
                'confidence_score': 0.0,
                'distance': 1.0,
                'details': 'No face detected in the sighting photo.'
            }

        distance = face_recognition.face_distance([enc1[0]], enc2[0])[0]
        confidence = max(0.0, round(1.0 - float(distance), 4))
        is_match = float(distance) < tolerance

        return {
            'is_match': is_match,
            'confidence_score': confidence,
            'distance': round(float(distance), 4),
            'details': (
                f"Face distance: {round(float(distance), 4)}. "
                f"{'MATCH FOUND!' if is_match else 'No match.'} "
                f"Confidence: {round(confidence * 100, 1)}%"
            )
        }

    except Exception as e:
        return {
            'is_match': False,
            'confidence_score': 0.0,
            'distance': 1.0,
            'details': f'Error during face comparison: {str(e)}'
        }


def extract_face(image_path):
    """
    Check whether at least one face is detectable in the image.
    Returns True if a face is found.
    If the library is unavailable, returns True (graceful passthrough — don't block uploads).
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return True   # allow uploads to proceed in demo mode

    try:
        image = face_recognition.load_image_file(image_path)
        locations = face_recognition.face_locations(image)
        return len(locations) > 0
    except Exception as e:
        print(f"extract_face error: {e}")
        return False


def batch_compare(police_photo_path, citizen_photos_list, tolerance=0.6):
    """
    Compare one police photo against multiple citizen sighting photos.
    Returns list sorted by confidence descending.
    """
    results = []
    for path in citizen_photos_list:
        result = compare_faces(police_photo_path, path, tolerance)
        result['photo_path'] = path
        results.append(result)
    results.sort(key=lambda x: x['confidence_score'], reverse=True)
    return results