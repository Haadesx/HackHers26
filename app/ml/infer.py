import cv2
import numpy as np
from typing import Optional
from typing import Dict, Any

from backend.app.video.decode import decode_video_bytes
from backend.app.video.sampling import sample_frames
from backend.app.video.quality import compute_quality_score
from backend.app.video.liveness import compute_liveness_score
from backend.app.video.presage_features import compute_presage_features
from backend.app.ml.model_loader import load_deepfake_model
from backend.app.ml.preprocess import preprocess_batch, resize_roi


def detect_face_haar(frame: np.ndarray, cascade: Optional[cv2.CascadeClassifier] = None) -> Optional[tuple]:
    """
    Detect face using Haar cascade.
    
    Returns:
        tuple: (x, y, w, h) or None if no face detected
    """
    if cascade is None:
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    
    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    if len(faces) > 0:
        x, y, w, h = faces[0]
        return (int(x), int(y), int(w), int(h))
    
    return None


def extract_face_roi(frame: np.ndarray, bbox: tuple) -> Optional[np.ndarray]:
    """Extract face ROI from frame using bounding box."""
    if bbox is None:
        return None
    
    x, y, w, h = bbox
    
    h_frame, w_frame = frame.shape[:2]
    
    x = max(0, x)
    y = max(0, y)
    w = min(w, w_frame - x)
    h = min(h, h_frame - y)
    
    if w <= 0 or h <= 0:
        return None
    
    roi = frame[y:y+h, x:x+w]
    
    return roi


def compute_temporal_inconsistency(rois: list, fake_probs: list) -> float:
    """
    Compute temporal inconsistency score.
    Deepfakes often have inconsistent fake probabilities across frames.
    """
    if len(fake_probs) < 2:
        return 0.0
    
    variance = np.var(fake_probs)
    mean_diff = np.mean(np.abs(np.diff(fake_probs)))
    
    inconsistency = variance + mean_diff
    
    return min(inconsistency * 2.0, 1.0)


def analyze_video_bytes(video_bytes: bytes, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entry point for video analysis.
    
    Args:
        video_bytes: Raw video file bytes
        config: Optional configuration dict
    
    Returns:
        dict with keys: deepfake_mean, deepfake_var, liveness, quality, presage, signals, presage_raw
    """
    if config is None:
        config = {}
    
    sample_interval = config.get("sample_interval", 15)
    max_frames = config.get("max_frames", 12)
    
    signals = []
    all_signals = []
    
    success, frames, decode_signals = decode_video_bytes(video_bytes)
    if not success:
        return {
            "deepfake_mean": 0.0,
            "deepfake_var": 0.0,
            "liveness": 0.0,
            "quality": 0.0,
            "presage": 0.0,
            "signals": decode_signals,
            "presage_raw": {
                "micro_motion": 0.0,
                "smoothness": 0.0,
                "periodicity_proxy": 0.0,
                "face_presence_ratio": 0.0
            }
        }
    
    all_signals.extend(decode_signals)
    
    sampled_frames, frame_indices, sample_signals = sample_frames(
        frames, sample_interval, max_frames
    )
    all_signals.extend(sample_signals)
    
    if len(sampled_frames) == 0:
        return {
            "deepfake_mean": 0.0,
            "deepfake_var": 0.0,
            "liveness": 0.0,
            "quality": 0.0,
            "presage": 0.0,
            "signals": all_signals + ["no_sampled_frames"],
            "presage_raw": {
                "micro_motion": 0.0,
                "smoothness": 0.0,
                "periodicity_proxy": 0.0,
                "face_presence_ratio": 0.0
            }
        }
    
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    face_bboxes = []
    rois = []
    
    for frame in sampled_frames:
        bbox = detect_face_haar(frame, cascade)
        face_bboxes.append(bbox)
        
        if bbox is not None:
            roi = extract_face_roi(frame, bbox)
            rois.append(roi)
        else:
            rois.append(None)
    
    quality, quality_signals = compute_quality_score(rois)
    all_signals.extend(quality_signals)
    
    if "decode_failed" in all_signals:
        return {
            "deepfake_mean": 0.0,
            "deepfake_var": 0.0,
            "liveness": 0.0,
            "quality": 0.0,
            "presage": 0.0,
            "signals": all_signals,
            "presage_raw": {
                "micro_motion": 0.0,
                "smoothness": 0.0,
                "periodicity_proxy": 0.0,
                "face_presence_ratio": 0.0
            }
        }
    
    liveness, liveness_signals = compute_liveness_score(
        list(sampled_frames), face_bboxes
    )
    all_signals.extend(liveness_signals)
    
    presage, presage_raw, presage_signals = compute_presage_features(
        list(sampled_frames), rois, face_bboxes
    )
    all_signals.extend(presage_signals)
    
    deepfake_model, is_fake = load_deepfake_model()
    if is_fake:
        signals.append("using_fake_model")
    
    preprocessed = []
    for roi in rois:
        if roi is not None and roi.size > 0:
            resized = resize_roi(roi, (224, 224))
            from backend.app.ml.preprocess import normalize_to_tensor
            tensor = normalize_to_tensor(resized)
            preprocessed.append(tensor)
        else:
            preprocessed.append(np.zeros((3, 224, 224), dtype=np.float32))
    
    fake_probs = deepfake_model.predict_batch(preprocessed)
    
    temporal_inconsistency = compute_temporal_inconsistency(rois, fake_probs)
    if temporal_inconsistency > 0.5:
        all_signals.append("temporal_inconsistency_detected")
    
    adjusted_probs = [p + 0.1 * temporal_inconsistency for p in fake_probs]
    
    deepfake_mean = float(np.mean(adjusted_probs)) if adjusted_probs else 0.5
    deepfake_var = float(np.var(adjusted_probs)) if len(adjusted_probs) > 1 else 0.0
    
    deepfake_mean = max(0.0, min(1.0, deepfake_mean))
    deepfake_var = max(0.0, min(1.0, deepfake_var))
    
    unique_signals = list(set(all_signals))
    
    return {
        "deepfake_mean": deepfake_mean,
        "deepfake_var": deepfake_var,
        "liveness": float(liveness),
        "quality": float(quality),
        "presage": float(presage),
        "signals": unique_signals,
        "presage_raw": {
            "micro_motion": float(presage_raw.get("micro_motion", 0.0)),
            "smoothness": float(presage_raw.get("smoothness", 0.0)),
            "periodicity_proxy": float(presage_raw.get("periodicity_proxy", 0.0)),
            "face_presence_ratio": float(presage_raw.get("face_presence_ratio", 0.0))
        }
    }
