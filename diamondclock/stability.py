"""Overlapping Allan deviation of contiguous fractional-frequency averages.

NIST SP 1065 Sec. 5.2.4, Eq. (10), printed p.16 (PDF p.26).
"""
import numpy as np
import pandas as pd


def averaging_factors(n, points=32, dt_s=1.):
    # Conservative maximum tau: N*dt/10; at least five disjoint pairs.
    if n < 20:
        raise ValueError("At least 20 samples required.")
    grid=np.rint(np.geomspace(1, n//10, points)).astype(int)
    # Include conventional 1,2,5-decade times whenever exactly representable.
    preferred=np.array([v*10.**k for k in range(-3,8) for v in (1,2,5)])
    m=np.rint(preferred/dt_s).astype(int)
    valid=(m>=1)&(m<=n//10)&np.isclose(m*dt_s,preferred,rtol=1e-10,atol=1e-12)
    return np.unique(np.r_[grid,m[valid]])


def overlapping_adev(y, dt_s=1., factors=None):
    """O(N) per tau. Pair count is NOT equivalent degrees of freedom.

    M4: z_j=(1/m) sum_{i=j}^{j+m-1} y_i;
        sigma_y^2=mean((z[j+m]-z[j])^2)/2.
    All inputs must be uniformly spaced contiguous interval averages.
    Mean removal improves cumulative-sum conditioning, not drift removal.
    """
    y = np.asarray(y, dtype=float)
    if y.ndim != 1 or len(y)<2 or not np.isfinite(y).all() or not np.isfinite(dt_s) or dt_s<=0:
        raise ValueError("Use a finite 1D series and positive sample interval.")
    if factors is None:
        factors = averaging_factors(len(y),dt_s=dt_s)
    cs = np.r_[0., np.cumsum(y-y.mean())]
    rows = []
    for m in factors:
        if not np.isfinite(m) or m != int(m) or m<1 or 2*m>len(y):
            raise ValueError("Averaging factors must be positive integers with 2*m <= N.")
        m = int(m)
        means = (cs[m:]-cs[:-m])/m
        delta = means[m:]-means[:-m]
        rows.append((m*dt_s, np.sqrt(.5*np.mean(delta**2)), len(delta), m))
    return pd.DataFrame(rows, columns=["tau_s", "adev", "overlapping_pairs", "m"])
