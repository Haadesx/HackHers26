import numpy as np
import cv2
from typing import Optional


def resize_roi(roi: np.ndarray, target_size: tuple = (224, 224)) -> np.ndarray:
    """Resize ROI to target dimensions."""
    if roi is None or roi.size == 0:
        return np.zeros((*target_size, 3), dtype=np.uint8)
    
    resized = cv2.resize(roi, target_size, interpolation=cv2.INTER_LINEAR)
    return resized


def normalize_to_tensor(frame: np.ndarray, mean: Optional[list] = None, std: Optional[list] = None) -> np.ndarray:
    """
    Normalize frame to float32 tensor format.
    
    Args:
        frame: Image array (H, W, C) in BGR format
        mean: Mean values for normalization [B, G, R]
        std: Std values for normalization [B, G, R]
    
    Returns:
        Normalized tensor in (C, H, W) format
    """
    if mean is None:
        mean = [0.485, 0.456, 0.406]
    if std is None:
        std = [0.229, 0.224, 0.225]
    
    frame_float = frame.astype(np.float32) / 255.0
    
    frame_bgr = frame_float[..., ::-1]
    
    mean_array = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
    std_array = np.array(std, dtype=np.float32).reshape(1, 1, 3)
    
    normalized = (frame_bgr - mean_array) / std_array
    
    tensor = np.transpose(normalized, (2, 0, 1))
    
    return tensor.astype(np.float32)


def preprocess_batch(rois: list[Optional[np.ndarray]], target_size: tuple = (224, 224)) -> np.ndarray:
    """
    Preprocess a batch of ROIs for model inference.
    
    Returns:
        Numpy array of shape (N, C, H, W)
    """
    tensors = []
    
    for roi in rois:
        if roi is None or roi.size == 0:
            tensor = np.zeros((3, target_size[1], target_size[0]), dtype=np.float32)
        else:
            resized = resize_roi(roi, target_size)
            tensor = normalize_to_tensor(resized)
        
        tensors.append(tensor)
    
    return np.stack(tensors, axis=0)


def apply_transforms(frame: np.ndarray) -> np.ndarray:
    """Apply standard transforms for deepfake detection."""
    resized = resize_roi(frame, (224, 224))
    tensor = normalize_to_tensor(resized)
    return tensor
