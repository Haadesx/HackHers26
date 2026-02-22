import os
import numpy as np
from typing import Optional


class FakeModel:
    """
    Fallback fake detection model using heuristics.
    Used when real model weights are not available.

    Calibrated to produce LOW scores (0.05-0.15) for real webcam faces
    and HIGH scores (0.5+) only for genuinely anomalous inputs.
    """

    def __init__(self):
        self.name = "FakeModel"

    def predict(self, frame_tensor: np.ndarray) -> float:
        """
        Compute fake probability using heuristic features.

        Calibrated so real faces produce scores in [0.05, 0.15].
        """
        if frame_tensor is None or frame_tensor.size == 0:
            return 0.1  # unknown → assume real

        features = []

        edge_score = self._detect_edge_artifacts(frame_tensor)
        features.append(edge_score)

        color_score = self._detect_color_abnormality(frame_tensor)
        features.append(color_score)

        texture_score = self._detect_texture_anomaly(frame_tensor)
        features.append(texture_score)

        fake_prob = np.mean(features) if features else 0.1

        return float(max(0.0, min(1.0, fake_prob)))

    def _to_hwc_uint8(self, frame: np.ndarray) -> np.ndarray:
        """Normalise tensor to HWC uint8 format."""
        if len(frame.shape) == 4:
            frame = frame[0]
        if len(frame.shape) == 3 and frame.shape[0] == 3:
            frame = np.transpose(frame, (1, 2, 0))
        if frame.max() <= 1.0:
            frame = (frame * 255).astype(np.uint8)
        else:
            frame = frame.astype(np.uint8)
        return frame

    def _detect_edge_artifacts(self, frame: np.ndarray) -> float:
        """
        Detect edge artifacts typical of fake videos.
        Real webcam faces have edge_strength ~10-30. Deepfakes often have
        sharper boundary artefacts pushing strength > 40.
        """
        frame = self._to_hwc_uint8(frame)
        gray = np.mean(frame, axis=2) if len(frame.shape) == 3 else frame.astype(float)

        sobel_x = np.abs(np.diff(gray, axis=1))
        sobel_y = np.abs(np.diff(gray, axis=0))
        edge_strength = np.mean(sobel_x) + np.mean(sobel_y)

        # Typical real face: edge_strength 10-30 → score 0.0-0.1
        # Deepfake artefacts: edge_strength 40+ → score 0.3+
        if edge_strength < 35:
            return edge_strength / 350.0  # 0.0 – 0.10
        return min((edge_strength - 35) / 30.0 * 0.5 + 0.1, 1.0)

    def _detect_color_abnormality(self, frame: np.ndarray) -> float:
        """
        Detect abnormal colour distribution.
        Real skin tones naturally have R > G > B, so R/G ≈ 1.05-1.25
        and G/B ≈ 1.0-1.15. Only flag if ratios are way outside that.
        """
        frame = self._to_hwc_uint8(frame)
        if len(frame.shape) < 3 or frame.shape[2] < 3:
            return 0.05

        r = np.mean(frame[..., 0].astype(float))
        g = np.mean(frame[..., 1].astype(float))
        b = np.mean(frame[..., 2].astype(float))

        rg_ratio = r / (g + 1e-6)
        gb_ratio = g / (b + 1e-6)

        # Natural skin: R/G in [0.9, 1.4], G/B in [0.85, 1.3]
        rg_deviation = max(0, abs(rg_ratio - 1.15) - 0.25)
        gb_deviation = max(0, abs(gb_ratio - 1.05) - 0.20)

        color_score = min((rg_deviation + gb_deviation) * 0.5, 1.0)
        return color_score

    def _detect_texture_anomaly(self, frame: np.ndarray) -> float:
        """
        Simple LBP-like texture consistency check.
        Real faces have natural texture variation; GAN-generated faces
        sometimes have unnaturally smooth or repetitive micro-textures.
        """
        frame = self._to_hwc_uint8(frame)
        gray = np.mean(frame, axis=2) if len(frame.shape) == 3 else frame.astype(float)

        # Local variance in small patches
        h, w = gray.shape[:2]
        if h < 16 or w < 16:
            return 0.05

        patch_size = 8
        variances = []
        for y in range(0, h - patch_size, patch_size):
            for x in range(0, w - patch_size, patch_size):
                patch = gray[y:y + patch_size, x:x + patch_size]
                variances.append(np.var(patch))

        if not variances:
            return 0.05

        mean_var = np.mean(variances)
        std_var = np.std(variances)

        # Real faces: varied texture (mean_var > 50, std_var > 30)
        # Over-smooth (GAN): mean_var < 20
        # Over-sharp (spliced): mean_var > 200
        if 20 < mean_var < 200 and std_var > 10:
            return 0.05  # normal texture
        elif mean_var < 20:
            return 0.3  # suspiciously smooth
        elif mean_var > 200:
            return 0.25  # suspiciously sharp
        else:
            return 0.1

    def predict_batch(self, frame_tensors: list[np.ndarray]) -> list[float]:
        """Predict fake probability for a batch of frames."""
        probs = [self.predict(ft) for ft in frame_tensors]

        # Inter-frame consistency: real faces have consistent low scores.
        # If variance across frames is very high, that's suspicious.
        if len(probs) >= 3:
            frame_var = np.var(probs)
            if frame_var > 0.05:
                # High variance across frames → bump all scores slightly
                probs = [min(p + 0.1, 1.0) for p in probs]

        return probs


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
