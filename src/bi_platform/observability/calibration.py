"""
Model Calibration Tracker
Track ML model confidence calibration over time

Based on LLM Observability patterns:
https://github.com/espirado/llm-observability

Metrics:
- ECE (Expected Calibration Error)
- MCE (Maximum Calibration Error)  
- Brier Score
- High-confidence failures
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np


@dataclass
class CalibrationSample:
    """Single prediction sample with ground truth"""
    prediction_confidence: float  # 0.0 - 1.0
    actual_correct: bool
    model_name: str
    task_type: str
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class CalibrationMetrics:
    """Calibration metrics for a set of predictions"""
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    brier_score: float  # Brier score
    n_samples: int
    high_confidence_failures: int
    reliability_data: Dict
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "ece": round(self.ece, 4),
            "mce": round(self.mce, 4),
            "brier_score": round(self.brier_score, 4),
            "n_samples": self.n_samples,
            "high_confidence_failures": self.high_confidence_failures,
            "reliability_data": self.reliability_data,
            "status": self.get_status(),
            "timestamp": self.timestamp.isoformat()
        }
    
    def get_status(self) -> str:
        """Get calibration status based on ECE"""
        if self.ece < 0.05:
            return "excellent"
        elif self.ece < 0.10:
            return "good"
        elif self.ece < 0.15:
            return "fair"
        else:
            return "poor"


class CalibrationTracker:
    """
    Track model calibration over time
    
    Usage:
        tracker = CalibrationTracker()
        
        # After making prediction
        tracker.add_sample(
            confidence=0.85,
            actual_correct=True,
            model_name="gpt-4-turbo",
            task_type="classification"
        )
        
        # Get metrics
        metrics = tracker.compute_metrics()
        print(f"ECE: {metrics.ece:.4f}")
    """
    
    def __init__(self, max_samples: int = 10000):
        self.samples: List[CalibrationSample] = []
        self.max_samples = max_samples
        
    def add_sample(
        self,
        confidence: float,
        actual_correct: bool,
        model_name: str,
        task_type: str,
        metadata: Optional[Dict] = None
    ):
        """Add a prediction sample for calibration tracking"""
        
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {confidence}")
        
        sample = CalibrationSample(
            prediction_confidence=confidence,
            actual_correct=actual_correct,
            model_name=model_name,
            task_type=task_type,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.samples.append(sample)
        
        # Keep only recent samples
        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples:]
    
    def compute_metrics(self, n_bins: int = 10) -> CalibrationMetrics:
        """
        Compute calibration metrics
        
        Args:
            n_bins: Number of bins for ECE/MCE calculation
            
        Returns:
            CalibrationMetrics with all metrics
        """
        
        if len(self.samples) < 10:
            raise ValueError("Need at least 10 samples to compute metrics")
        
        ece = self._compute_ece(n_bins)
        mce = self._compute_mce(n_bins)
        brier = self._compute_brier_score()
        high_conf_failures = len(self._get_high_confidence_failures())
        reliability_data = self._get_reliability_diagram_data(n_bins)
        
        return CalibrationMetrics(
            ece=ece,
            mce=mce,
            brier_score=brier,
            n_samples=len(self.samples),
            high_confidence_failures=high_conf_failures,
            reliability_data=reliability_data,
            timestamp=datetime.utcnow()
        )
    
    def _compute_ece(self, n_bins: int = 10) -> float:
        """
        Compute Expected Calibration Error
        
        ECE = Average of |confidence - accuracy| across all bins
        Perfect calibration = 0.0
        """
        
        confidences = np.array([s.prediction_confidence for s in self.samples])
        corrects = np.array([1.0 if s.actual_correct else 0.0 for s in self.samples])
        
        # Create bins
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        
        ece = 0.0
        total_samples = len(self.samples)
        
        for i in range(n_bins):
            # Find samples in this bin
            in_bin = (confidences >= bin_boundaries[i]) & (confidences < bin_boundaries[i + 1])
            
            if i == n_bins - 1:  # Last bin includes upper boundary
                in_bin = (confidences >= bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
            
            if np.sum(in_bin) > 0:
                bin_accuracy = np.mean(corrects[in_bin])
                bin_confidence = np.mean(confidences[in_bin])
                bin_weight = np.sum(in_bin) / total_samples
                
                ece += bin_weight * abs(bin_accuracy - bin_confidence)
        
        return float(ece)
    
    def _compute_mce(self, n_bins: int = 10) -> float:
        """
        Compute Maximum Calibration Error
        
        MCE = Maximum of |confidence - accuracy| across all bins
        """
        
        confidences = np.array([s.prediction_confidence for s in self.samples])
        corrects = np.array([1.0 if s.actual_correct else 0.0 for s in self.samples])
        
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        
        max_error = 0.0
        
        for i in range(n_bins):
            in_bin = (confidences >= bin_boundaries[i]) & (confidences < bin_boundaries[i + 1])
            
            if i == n_bins - 1:
                in_bin = (confidences >= bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
            
            if np.sum(in_bin) > 0:
                bin_accuracy = np.mean(corrects[in_bin])
                bin_confidence = np.mean(confidences[in_bin])
                error = abs(bin_accuracy - bin_confidence)
                
                max_error = max(max_error, error)
        
        return float(max_error)
    
    def _compute_brier_score(self) -> float:
        """
        Compute Brier Score
        
        Measures accuracy of probabilistic predictions
        Perfect score = 0.0, worst = 1.0
        """
        
        score = 0.0
        for sample in self.samples:
            actual = 1.0 if sample.actual_correct else 0.0
            score += (sample.prediction_confidence - actual) ** 2
        
        return score / len(self.samples)
    
    def _get_high_confidence_failures(
        self,
        confidence_threshold: float = 0.9
    ) -> List[CalibrationSample]:
        """
        Get predictions that were highly confident but wrong
        
        These are the most concerning - model was confident but incorrect
        """
        
        return [
            s for s in self.samples
            if s.prediction_confidence >= confidence_threshold
            and not s.actual_correct
        ]
    
    def _get_reliability_diagram_data(self, n_bins: int = 10) -> Dict:
        """
        Get data for reliability diagram
        
        Plots confidence vs accuracy
        Perfect calibration = diagonal line
        Overconfident = above diagonal
        Underconfident = below diagonal
        """
        
        confidences = np.array([s.prediction_confidence for s in self.samples])
        corrects = np.array([1.0 if s.actual_correct else 0.0 for s in self.samples])
        
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        
        bin_confidences = []
        bin_accuracies = []
        bin_counts = []
        
        for i in range(n_bins):
            in_bin = (confidences >= bin_boundaries[i]) & (confidences < bin_boundaries[i + 1])
            
            if i == n_bins - 1:
                in_bin = (confidences >= bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
            
            bin_center = (bin_boundaries[i] + bin_boundaries[i + 1]) / 2
            
            if np.sum(in_bin) > 0:
                avg_confidence = float(np.mean(confidences[in_bin]))
                accuracy = float(np.mean(corrects[in_bin]))
                count = int(np.sum(in_bin))
            else:
                avg_confidence = bin_center
                accuracy = None
                count = 0
            
            bin_confidences.append(avg_confidence)
            bin_accuracies.append(accuracy)
            bin_counts.append(count)
        
        return {
            "bin_confidences": bin_confidences,
            "bin_accuracies": bin_accuracies,
            "bin_counts": bin_counts,
            "perfect_calibration": list(np.linspace(0.05, 0.95, n_bins))
        }
    
    def get_metrics_by_model(self) -> Dict[str, CalibrationMetrics]:
        """Get calibration metrics broken down by model"""
        
        models = set(s.model_name for s in self.samples)
        
        metrics_by_model = {}
        for model in models:
            model_samples = [s for s in self.samples if s.model_name == model]
            
            if len(model_samples) >= 10:
                # Temporarily store samples
                temp_samples = self.samples
                self.samples = model_samples
                
                metrics = self.compute_metrics()
                metrics_by_model[model] = metrics
                
                # Restore
                self.samples = temp_samples
        
        return metrics_by_model
    
    def get_status(self) -> Dict:
        """Get current calibration status"""
        
        if len(self.samples) < 10:
            return {
                "status": "insufficient_data",
                "n_samples": len(self.samples),
                "message": "Need at least 10 samples"
            }
        
        try:
            metrics = self.compute_metrics()
            return {
                "status": metrics.get_status(),
                "ece": metrics.ece,
                "n_samples": metrics.n_samples,
                "high_confidence_failures": metrics.high_confidence_failures
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


# Singleton tracker
_tracker_instance = None

def get_tracker() -> CalibrationTracker:
    """Get calibration tracker singleton"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = CalibrationTracker()
    return _tracker_instance
```

