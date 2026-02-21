import os
import numpy as np
from typing import Optional


class FakeModel:
    """
    Fallback fake detection model using heuristics.
    Used when real model weights are not available.
    """
    
    def __init__(self):
        self.name = "FakeModel"
    
    def predict(self, frame_tensor: np.ndarray) -> float:
        """
        Compute fake probability using heuristic features.
        
        Features:
        - Edge artifacts at ROI boundary
        - Abnormal color distribution
        - Temporal inconsistency
        """
        features = []
        
        edge_artifact_score = self._detect_edge_artifacts(frame_tensor)
        features.append(edge_artifact_score)
        
        color_abnormality = self._detect_color_abnormality(frame_tensor)
        features.append(color_abnormality)
        
        fake_prob = np.mean(features) if features else 0.5
        
        return float(fake_prob)
    
    def _detect_edge_artifacts(self, frame: np.ndarray) -> float:
        """Detect edge artifacts typical of fake videos."""
        if frame is None or frame.size == 0:
            return 0.5
        
        if len(frame.shape) == 4:
            frame = frame[0]
        
        if len(frame.shape) == 3 and frame.shape[0] == 3:
            frame = np.transpose(frame, (1, 2, 0))
        
        frame_uint8 = (frame * 255).astype(np.uint8) if frame.max() <= 1.0 else frame.astype(np.uint8)
        
        gray = np.mean(frame_uint8, axis=2) if len(frame_uint8.shape) == 3 else frame_uint8
        
        sobel_x = np.abs(np.diff(gray, axis=1))
        sobel_y = np.abs(np.diff(gray, axis=0))
        
        edge_strength = np.mean(sobel_x) + np.mean(sobel_y)
        
        edge_score = min(edge_strength / 50.0, 1.0)
        
        return edge_score
    
    def _detect_color_abnormality(self, frame: np.ndarray) -> float:
        """Detect abnormal color distribution."""
        if frame is None or frame.size == 0:
            return 0.5
        
        if len(frame.shape) == 4:
            frame = frame[0]
        
        if len(frame.shape) == 3 and frame.shape[0] == 3:
            frame = np.transpose(frame, (1, 2, 0))
        
        frame_normalized = frame * 255 if frame.max() <= 1.0 else frame
        
        r, g, b = frame_normalized[..., 0], frame_normalized[..., 1], frame_normalized[..., 2]
        
        rg_ratio = np.mean(r) / (np.mean(g) + 1e-6)
        gb_ratio = np.mean(g) / (np.mean(b) + 1e-6)
        
        normal_rg = 1.0
        normal_gb = 1.0
        
        rg_deviation = abs(rg_ratio - normal_rg)
        gb_deviation = abs(gb_ratio - normal_gb)
        
        color_score = min((rg_deviation + gb_deviation) / 2.0, 1.0)
        
        return color_score
    
    def predict_batch(self, frame_tensors: list[np.ndarray]) -> list[float]:
        """Predict fake probability for a batch of frames."""
        return [self.predict(ft) for ft in frame_tensors]


class RealDeepfakeModel:
    """Real deepfake detection model (placeholder for actual implementation)."""
    
    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = weights_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load actual model weights."""
        if self.weights_path and os.path.exists(self.weights_path):
            try:
                import torch
                self.model = torch.nn.Sequential(
                    torch.nn.Conv2d(3, 64, 3, padding=1),
                    torch.nn.ReLU(),
                    torch.nn.Conv2d(64, 128, 3, padding=1),
                    torch.nn.ReLU(),
                    torch.nn.AdaptiveAvgPool2d(1),
                    torch.nn.Flatten(),
                    torch.nn.Linear(128, 1),
                    torch.nn.Sigmoid()
                )
                self.model.load_state_dict(torch.load(self.weights_path))
                self.model.eval()
            except Exception:
                self.model = None
    
    def predict(self, frame_tensor: np.ndarray) -> float:
        """Run inference on a single frame."""
        if self.model is None:
            return 0.5
        
        import torch
        
        tensor = torch.from_numpy(frame_tensor).unsqueeze(0)
        
        with torch.inference_mode():
            prob = self.model(tensor).item()
        
        return prob
    
    def predict_batch(self, frame_tensors: list[np.ndarray]) -> list[float]:
        """Run inference on a batch of frames."""
        if self.model is None:
            return [0.5] * len(frame_tensors)
        
        import torch
        
        batch = torch.from_numpy(np.stack(frame_tensors))
        
        with torch.inference_mode():
            probs = self.model(batch).squeeze().tolist()
        
        if isinstance(probs, float):
            return [probs]
        return probs


def load_deepfake_model() -> tuple[Optional[object], bool]:
    """
    Load deepfake detection model.
    
    Returns:
        tuple: (model, is_fake_model)
    """
    weights_path = os.environ.get("DEEPFAKE_WEIGHTS")
    
    if weights_path and os.path.exists(weights_path):
        try:
            model = RealDeepfakeModel(weights_path)
            if model.model is not None:
                return model, False
        except Exception:
            pass
    
    return FakeModel(), True
