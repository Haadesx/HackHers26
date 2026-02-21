import numpy as np
from typing import Optional


def sample_frames(
    frames: np.ndarray,
    sample_interval: int = 15,
    max_frames: int = 12
) -> tuple[np.ndarray, list[int], list[str]]:
    """
    Sample frames from video at regular intervals.
    
    Args:
        frames: Array of all frames (H, W, C) or (N, H, W, C)
        sample_interval: Interval between sampled frames
        max_frames: Maximum number of frames to sample
    
    Returns:
        tuple: (sampled_frames, frame_indices, signals)
    """
    signals = []
    total_frames = len(frames)
    
    if total_frames == 0:
        return np.array([]), [], ["no_frames_to_sample"]
    
    indices = list(range(0, total_frames, sample_interval))
    
    if len(indices) > max_frames:
        indices = indices[:max_frames]
        signals.append("max_frames_limited")
    
    sampled = frames[indices]
    
    if len(sampled) < 3:
        signals.append("low_frame_count")
    
    return sampled, indices, signals


def get_frame_indices(
    total_frames: int,
    sample_interval: int = 15,
    max_frames: int = 12
) -> list[int]:
    """Get indices for frame sampling without extracting frames."""
    indices = list(range(0, total_frames, sample_interval))
    return indices[:max_frames]
