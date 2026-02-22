import cv2
import numpy as np
import tempfile
import os
from typing import Optional


def _get_suffix(video_bytes: bytes) -> str:
    # WebM magic number
    if video_bytes.startswith(b'\x1a\x45\xdf\xa3'):
        return '.webm'
    # QuickTime / MP4 headers
    return '.mp4'

def decode_video_bytes(video_bytes: bytes) -> tuple[bool, Optional[np.ndarray], list[str]]:
    """
    Decode video bytes using OpenCV.
    
    Returns:
        tuple: (success, frames_array, signals)
    """
    signals = []
    
    suffix = _get_suffix(video_bytes)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(video_bytes)
        tmp_path = tmp_file.name
    
    try:
        cap = cv2.VideoCapture(tmp_path)
        
        if not cap.isOpened():
            os.unlink(tmp_path)
            return False, None, ["decode_failed"]
        
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        
        cap.release()
        os.unlink(tmp_path)
        
        if len(frames) == 0:
            signals.append("no_frames")
            return False, None, signals
        
        return True, np.array(frames), signals
        
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        signals.append(f"decode_error: {str(e)}")
        return False, None, signals


def get_video_info(video_bytes: bytes) -> dict:
    """Get video metadata without full decode."""
    suffix = _get_suffix(video_bytes)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(video_bytes)
        tmp_path = tmp_file.name
    
    try:
        cap = cv2.VideoCapture(tmp_path)
        info = {
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
        cap.release()
        os.unlink(tmp_path)
        return info
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return {"frame_count": 0, "fps": 0, "width": 0, "height": 0}
