import cv2
import numpy as np
from typing import Optional


def compute_micro_motion_energy(roi: np.ndarray) -> float:
    """
    Compute micro-motion energy within cheeks/forehead region.
    Real faces have subtle micro-motions.
    """
    if roi is None or roi.size == 0:
        return 0.0
    
    h, w = roi.shape[:2]
    
    forehead_roi = roi[int(h*0.1):int(h*0.35), int(w*0.25):int(w*0.75)]
    left_cheek_roi = roi[int(h*0.5):int(h*0.75), int(w*0.1):int(w*0.35)]
    right_cheek_roi = roi[int(h*0.5):int(h*0.75), int(w*0.65):int(w*0.9)]
    
    regions = [forehead_roi, left_cheek_roi, right_cheek_roi]
    energies = []
    
    for region in regions:
        if region.size > 0:
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
            variance = np.var(gray)
            energies.append(min(variance / 1000.0, 1.0))
    
    return np.mean(energies) if energies else 0.0


def compute_motion_smoothness(flows: list[np.ndarray]) -> float:
    """
    Compute motion smoothness - natural motion is smooth, jittery indicates fake.
    """
    if len(flows) < 2:
        return 0.5
    
    smoothness_scores = []
    
    for i in range(len(flows) - 1):
        flow_curr = flows[i]
        flow_next = flows[i + 1]
        
        if flow_curr.size == 0 or flow_next.size == 0:
            continue
        
        diff = np.abs(flow_curr - flow_next)
        jitter = np.mean(diff)
        
        smoothness = max(0.0, 1.0 - jitter / 5.0)
        smoothness_scores.append(smoothness)
    
    return np.mean(smoothness_scores) if smoothness_scores else 0.5


def compute_periodicity_proxy(frames: list[np.ndarray]) -> float:
    """
    Compute periodicity proxy using mean green channel changes.
    Screen replays may show periodic patterns.
    """
    if len(frames) < 3:
        return 0.0
    
    green_means = []
    for frame in frames:
        if frame is not None and frame.size > 0:
            green_channel = frame[:, :, 1] if len(frame.shape) == 3 else frame
            green_means.append(np.mean(green_channel))
    
    if len(green_means) < 3:
        return 0.0
    
    green_means = np.array(green_means)
    differences = np.diff(green_means)
    
    autocorr = np.correlate(differences, differences, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    
    if len(autocorr) > 2:
        peaks = np.where((autocorr[1:-1] > autocorr[:-2]) & (autocorr[1:-1] > autocorr[2:]))[0]
        if len(peaks) > 0:
            periodicity = np.mean(autocorr[peaks + 1]) / (np.var(differences) + 1e-6)
            return min(periodicity / 10.0, 1.0)
    
    return 0.0


def compute_presage_features(
    frames: list[np.ndarray],
    rois: list[Optional[np.ndarray]],
    face_bboxes: list[Optional[tuple]]
) -> tuple[float, dict, list[str]]:
    """
    Compute Presage-like human sensing score.
    
    Returns:
        tuple: (presage_score, presage_raw_dict, signals)
    """
    signals = []
    
    total_frames = len(frames)
    if total_frames == 0:
        return 0.0, {"micro_motion": 0.0, "smoothness": 0.0, "periodicity_proxy": 0.0, "face_presence_ratio": 0.0}, signals
    
    frames_with_face = sum(1 for bbox in face_bboxes if bbox is not None)
    face_presence_ratio = frames_with_face / total_frames
    
    micro_motions = []
    for roi in rois:
        if roi is not None and roi.size > 0:
            micro_motions.append(compute_micro_motion_energy(roi))
    
    micro_motion = np.mean(micro_motions) if micro_motions else 0.0
    
    flows = []
    for i in range(len(frames) - 1):
        flow = cv2.calcOpticalFlowFarneback(
            cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(frames[i+1], cv2.COLOR_BGR2GRAY),
            None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        flows.append(flow)
    
    smoothness = compute_motion_smoothness(flows)
    periodicity_proxy = compute_periodicity_proxy(frames)
    
    presage_raw = {
        "micro_motion": float(micro_motion),
        "smoothness": float(smoothness),
        "periodicity_proxy": float(periodicity_proxy),
        "face_presence_ratio": float(face_presence_ratio)
    }
    
    presage = (
        0.35 * micro_motion +
        0.35 * smoothness +
        0.15 * (1.0 - periodicity_proxy) +
        0.15 * face_presence_ratio
    )
    presage = max(0.0, min(1.0, presage))
    
    if micro_motion < 0.2:
        signals.append("low_micro_motion")
    if smoothness < 0.4:
        signals.append("unnatural_motion")
    if periodicity_proxy > 0.7:
        signals.append("periodic_pattern_detected")
    
    return presage, presage_raw, signals
