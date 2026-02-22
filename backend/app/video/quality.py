import cv2
import numpy as np
from typing import Optional


def compute_blur_score(roi: np.ndarray) -> float:
    """
    Compute blur score using variance of Laplacian.
    Higher variance = less blur = better quality.
    """
    if roi.size == 0:
        return 0.0
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()
    
    # Lowered from 500 to 150 to be more forgiving for webcams
    normalized = min(variance / 150.0, 1.0)
    return normalized


def compute_brightness_score(roi: np.ndarray) -> float:
    """
    Compute brightness score using mean grayscale intensity.
    Optimal brightness is around 100-150.
    """
    if roi.size == 0:
        return 0.0
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
    mean_intensity = np.mean(gray)
    
    # Widened from 80-180 to 50-200 to allow dimmer/brighter indoor lighting
    optimal_low, optimal_high = 50, 200
    if optimal_low <= mean_intensity <= optimal_high:
        return 1.0
    elif mean_intensity < optimal_low:
        return mean_intensity / optimal_low
    else:
        return max(0.0, 1.0 - (mean_intensity - optimal_high) / 100.0)


def compute_face_presence_ratio(faces_detected: list, total_frames: int) -> float:
    """Compute ratio of frames with detected face."""
    if total_frames == 0:
        return 0.0
    frames_with_face = sum(1 for f in faces_detected if f is not None)
    return frames_with_face / total_frames


def compute_quality_score(
    rois: list[Optional[np.ndarray]],
    blur_weight: float = 0.4,
    brightness_weight: float = 0.3,
    face_presence_weight: float = 0.3
) -> tuple[float, list[str]]:
    """
    Compute overall quality score from face ROIs.
    
    Returns:
        tuple: (quality_score, signals)
    """
    signals = []
    total_frames = len(rois)
    
    if total_frames == 0:
        return 0.0, ["no_rois"]
    
    blur_scores = []
    brightness_scores = []
    faces_detected = []
    
    for roi in rois:
        if roi is None or roi.size == 0:
            blur_scores.append(0.0)
            brightness_scores.append(0.0)
            faces_detected.append(None)
        else:
            blur_scores.append(compute_blur_score(roi))
            brightness_scores.append(compute_brightness_score(roi))
            faces_detected.append(roi)
    
    face_presence_ratio = compute_face_presence_ratio(faces_detected, total_frames)
    
    avg_blur = np.mean(blur_scores) if blur_scores else 0.0
    avg_brightness = np.mean(brightness_scores) if brightness_scores else 0.0
    
    quality = (
        blur_weight * avg_blur +
        brightness_weight * avg_brightness +
        face_presence_weight * face_presence_ratio
    )
    
    quality = max(0.0, min(1.0, quality))
    
    if face_presence_ratio < 0.5:
        signals.append("low_face_presence")
    if avg_blur < 0.3:
        signals.append("blurry_video")
    if avg_brightness < 0.3:
        signals.append("poor_lighting")
    
    return quality, signals
