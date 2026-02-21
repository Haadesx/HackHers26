import cv2
import numpy as np
from typing import Optional


def compute_optical_flow(prev_frame: np.ndarray, curr_frame: np.ndarray) -> np.ndarray:
    """Compute dense optical flow between two frames."""
    if prev_frame is None or curr_frame is None:
        return np.array([])
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0
    )
    return flow


def compute_motion_magnitude(flow: np.ndarray) -> float:
    """Compute average motion magnitude from optical flow."""
    if flow.size == 0:
        return 0.0
    
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    return float(np.mean(magnitude))


def compute_non_rigid_ratio(flow: np.ndarray) -> float:
    """
    Compute ratio of non-rigid motion.
    Real faces have more non-rigid (local) motion than screen replays.
    """
    if flow.size == 0:
        return 0.0
    
    flow_x, flow_y = flow[..., 0], flow[..., 1]
    
    grad_x = np.gradient(flow_x, axis=0)
    grad_y = np.gradient(flow_y, axis=1)
    
    divergence = grad_x + grad_y
    curl = np.gradient(flow_y, axis=0) - np.gradient(flow_x, axis=1)
    
    non_rigid_energy = np.mean(np.abs(divergence)) + np.mean(np.abs(curl))
    global_flow = np.mean(np.abs(flow_x)) + np.mean(np.abs(flow_y))
    
    if global_flow == 0:
        return 0.5
    
    non_rigid_ratio = non_rigid_energy / (global_flow + 1e-6)
    
    return min(non_rigid_ratio / 2.0, 1.0)


def compute_liveness_score(
    frames: list[np.ndarray],
    face_bboxes: list[Optional[tuple]],
    motion_threshold: float = 2.0
) -> tuple[float, list[str]]:
    """
    Compute liveness score based on motion compliance and non-rigid motion.
    
    Args:
        frames: List of sampled frames
        face_bboxes: List of face bounding boxes (x, y, w, h) or None
        motion_threshold: Minimum motion to consider as responsive
    
    Returns:
        tuple: (liveness_score, signals)
    """
    signals = []
    
    if len(frames) < 2:
        return 0.5, ["insufficient_frames_for_liveness"]
    
    bbox_centers = []
    for bbox in face_bboxes:
        if bbox is not None:
            x, y, w, h = bbox
            bbox_centers.append((x + w // 2, y + h // 2))
        else:
            bbox_centers.append(None)
    
    valid_centers = [c for c in bbox_centers if c is not None]
    if len(valid_centers) >= 2:
        displacements = []
        for i in range(1, len(valid_centers)):
            dx = valid_centers[i][0] - valid_centers[i-1][0]
            dy = valid_centers[i][1] - valid_centers[i-1][1]
            displacements.append(np.sqrt(dx**2 + dy**2))
        
        avg_displacement = np.mean(displacements) if displacements else 0
        
        if avg_displacement < motion_threshold:
            signals.append("low_motion")
    else:
        avg_displacement = 0
    
    non_rigid_ratios = []
    for i in range(len(frames) - 1):
        roi_current = None
        for j, bbox in enumerate(face_bboxes[i+1:]):
            if bbox is not None:
                x, y, w, h = bbox
                roi_current = frames[i+1][y:y+h, x:x+w]
                break
        
        if roi_current is not None and roi_current.size > 0:
            flow = compute_optical_flow(frames[i], frames[i+1])
            if flow.size > 0:
                non_rigid = compute_non_rigid_ratio(flow)
                non_rigid_ratios.append(non_rigid)
    
    if not non_rigid_ratios:
        non_rigid_ratios = [0.5]
    
    avg_non_rigid = np.mean(non_rigid_ratios)
    
    if avg_non_rigid < 0.3:
        signals.append("rigid_motion_suspected")
    
    motion_compliance = min(avg_displacement / 20.0, 1.0)
    
    liveness = 0.4 * motion_compliance + 0.6 * avg_non_rigid
    liveness = max(0.0, min(1.0, liveness))
    
    return liveness, signals
