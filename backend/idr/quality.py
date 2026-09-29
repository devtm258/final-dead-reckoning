"""Bounded, causal sensor diagnostics. Flags describe suspicion, not labelled faults."""
from collections import deque
import numpy as np


class SensorQuality:
    def __init__(self, cutoff=2., window=11):
        if not 0 < cutoff <= 4.:
            raise ValueError('Cutoff must be in (0, 4] Hz for this 10 Hz pipeline.')
        self.cutoff = cutoff
        self.window = window
        self.reset()

    def reset(self):
        self.history = deque(maxlen=self.window)
        self.filtered = None

    def step(self, accel, gyro, dt):
        values = np.r_[accel, gyro].astype(float)
        if not np.isfinite(values).all() or not np.isfinite(dt) or not 0 < dt <= .5:
            self.reset()
            raise ValueError('Invalid sensor reading or timestamp gap: reinitialize; no sample was imputed.')
        flags = np.zeros(6, dtype=bool)
        if len(self.history) >= self.window:
            hist = np.asarray(self.history)
            med = np.median(hist, axis=0)
            mad = np.median(np.abs(hist - med), axis=0)
            # Physical floors keep quiet, near-zero MAD windows from flagging every change.
            threshold = np.maximum(4.5 * 1.4826 * mad, [.8, .8, .8, .08, .08, .08])
            flags = np.abs(values - med) > threshold
        self.history.append(values.copy())
        alpha = 1. - np.exp(-2 * np.pi * self.cutoff * dt)
        self.filtered = values.copy() if self.filtered is None else self.filtered + alpha * (values - self.filtered)
        return self.filtered.copy(), {'accel_flag': bool(flags[:3].any()),
                                     'gyro_flag': bool(flags[3:].any()),
                                     'timing_flag': bool(abs(dt - .1) > .05)}


def adaptation(flags, yaw_rate, accel):
    """Heuristic ablation, not a calibrated probability-to-covariance mapping."""
    return {'accel_process_scale': 4. if flags['accel_flag'] else 1.,
            'gyro_process_scale': 4. if flags['gyro_flag'] else 1.,
            'nhc_scale': 4. if abs(yaw_rate) > .35 or np.linalg.norm(accel) > 4. else 1.,
            # Raw-input speed model retains its own learned uncertainty unchanged.
            'speed_scale': 1.}
