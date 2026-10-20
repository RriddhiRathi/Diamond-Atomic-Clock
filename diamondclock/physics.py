"""Ground-state 14NV Hamiltonian in cyclic frequency units (Hz), H/h.

Sources: L2023 Eq. (1), Table II; L2026 Eq. (1), Appendix A.
No angular-frequency 2*pi factors belong in this Hamiltonian.
"""
from dataclasses import dataclass, field, fields
import numpy as np
from scipy.optimize import linear_sum_assignment


def parameter(value, unit, source, locator, note=""):
    return field(default=value, metadata=dict(unit=unit, source=source, locator=locator, note=note))


@dataclass(frozen=True)
class Physics:
    T0_K: float = parameter(297., "K", "L2023", "Table II, p. 064084-5", "Expansion temperature")
    D0_Hz: float = parameter(2_870_280_000., "Hz", "L2023", "Table II, p. 064084-5")
    D1_Hz_K: float = parameter(-72_500., "Hz/K", "L2023", "Table II, p. 064084-5")
    D2_Hz_K2: float = parameter(-390., "Hz/K^2", "L2023", "Table II, p. 064084-5", "Second derivative, not polynomial coefficient")
    Q0_Hz: float = parameter(-4_945_880., "Hz", "L2023", "Table II, p. 064084-5", "Signed quadrupole parameter")
    Q1_Hz_K: float = parameter(35.5, "Hz/K", "L2023", "Table II, p. 064084-5")
    Q2_Hz_K2: float = parameter(.22, "Hz/K^2", "L2023", "Table II, p. 064084-5")
    Apar0_Hz: float = parameter(-2_165_190., "Hz", "L2023", "Table II, p. 064084-5")
    Apar1_Hz_K: float = parameter(197., "Hz/K", "L2023", "Table II, p. 064084-5")
    Apar2_Hz_K2: float = parameter(.73, "Hz/K^2", "L2023", "Table II, p. 064084-5")
    Aperp0_Hz: float = parameter(-2_635_000., "Hz", "L2023", "Table II, p. 064084-5")
    Aperp1_Hz_K: float = parameter(154., "Hz/K", "L2023", "Table II, p. 064084-5")
    Aperp2_Hz_K2: float = parameter(.53, "Hz/K^2", "L2023", "Table II, p. 064084-5")
    gamma_e_Hz_G: float = parameter(2_803_300., "Hz/G", "F2009", "Sec. IV, p. 075203-4; cyclic value quoted in L2023 Sec. II", "From axial g=2.0029(2); scalar gamma approximation also used for small Bx, as in L2023")
    gamma_n_Hz_G: float = parameter(307.59, "Hz/G", "L2023", "Sec. IV, Eq. (4), p. 064084-6; Sec. II, p. 064084-2", "14N value from measured gamma ratio and literature electron gamma; Hamiltonian uses minus sign")


def parameter_rows(obj):
    return [dict(parameter=f.name, value=getattr(obj, f.name), **dict(f.metadata)) for f in fields(obj)]


_s = np.sqrt(2.)
SX = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], complex) / _s
SY = np.array([[0, -1j, 0], [1j, 0, -1j], [0, 1j, 0]], complex) / _s
SZ = np.diag([1., 0., -1.])
ID = np.eye(3)
S = [np.kron(x, ID) for x in (SX, SY, SZ)]
I = [np.kron(ID, x) for x in (SX, SY, SZ)]
DZ, QZ = S[2] @ S[2], I[2] @ I[2]
APAR, APERP = S[2] @ I[2], S[0] @ I[0] + S[1] @ I[1]
LABELS = [(ms, mi) for ms in (1, 0, -1) for mi in (1, 0, -1)]


def thermal_parameters(T_K, p=Physics()):
    """M1: local Taylor expansion X0 + X' dT + 1/2 X'' dT^2."""
    d = np.asarray(T_K) - p.T0_K
    return tuple(getattr(p, x+"0_Hz") + getattr(p, x+"1_Hz_K")*d
                 + .5*getattr(p, x+"2_Hz_K2")*d*d for x in ("D", "Q", "Apar", "Aperp"))


def hamiltonian(T_K, Bz_G, Bx_G=0., p=Physics()):
    """L2023 Eq. (1). Spin-one electron and spin-one 14N, full 9x9 matrix.

    Axial strain is included in D; fluctuating transverse strain/electric fields
    are excluded. Transverse Zeeman terms follow L2023 Eq. (1).
    """
    T, bz, bx = np.broadcast_arrays(T_K, Bz_G, Bx_G)
    d, q, apar, aperp = thermal_parameters(T, p)
    return (d[..., None, None]*DZ + q[..., None, None]*QZ
            + apar[..., None, None]*APAR + aperp[..., None, None]*APERP
            + bz[..., None, None]*(p.gamma_e_Hz_G*S[2]-p.gamma_n_Hz_G*I[2])
            + bx[..., None, None]*(p.gamma_e_Hz_G*S[0]-p.gamma_n_Hz_G*I[0]))


def reference_states(Bz_G=475., Bx_G=0., p=Physics()):
    """Label reference eigenstates by globally unique maximum bare-state overlap."""
    energies, vecs = np.linalg.eigh(hamiltonian(p.T0_K, Bz_G, Bx_G, p))
    bare, order = linear_sum_assignment(-np.abs(vecs)**2)
    order = order[np.argsort(bare)]
    return energies[order], vecs[:, order]


def observables(T_K, Bz_G, Bx_G=0., p=Physics(), reference=None):
    """Track reference eigenvectors; return f+, f-, f1, f2, Dobs, Qobs.

    M2: Dobs=(f+ + f-)/2; Qobs=-(f1+f2)/2 (signed).
    Reference overlap is checked; crossings/strong mixing are rejected.
    """
    T, bz, bx = np.broadcast_arrays(T_K, Bz_G, Bx_G)
    shape = T.shape
    T, bz, bx = T.ravel(), bz.ravel(), bx.ravel()
    if reference is None:
        reference = reference_states(float(bz[0]), float(bx[0]), p)[1]
    result = []
    for start in range(0, len(T), 4096):
        e, v = np.linalg.eigh(hamiltonian(T[start:start+4096], bz[start:start+4096], bx[start:start+4096], p))
        overlap = np.abs(np.einsum('ai,naj->nij', reference.conj(), v))**2
        order = overlap.argmax(axis=2)
        if np.any(np.diff(np.sort(order, axis=1), axis=1) == 0) or np.min(overlap.max(axis=2)) < .8:
            raise ValueError("Eigenstate tracking ambiguous; reduce field/temperature excursions.")
        e = np.take_along_axis(e, order, axis=1)
        # Basis index: (+1,+1)=0, (0,+1)=3, (-1,+1)=6; nuclear (0,0)=4, (0,-1)=5.
        fp, fm = e[:, 0]-e[:, 3], e[:, 6]-e[:, 3]
        f1, f2 = e[:, 4]-e[:, 3], e[:, 4]-e[:, 5]
        result.append(np.stack([fp, fm, f1, f2, (fp+fm)/2, -(f1+f2)/2], axis=-1))
    return np.concatenate(result).reshape(shape+(6,))


def calibration(Bz_G=475., Bx_G=0., p=Physics()):
    """M3: calibrate actual half-sum slopes, including hyperfine corrections.

    L2026 Appendix A explicitly distinguishes D,Q from measured half-sums.
    Central differences use 0.01 K. Composite weights follow Eq. (5).
    """
    ref = reference_states(Bz_G, Bx_G, p)[1]
    f0 = observables(p.T0_K, Bz_G, Bx_G, p, ref)
    h = .01
    slope = (observables(p.T0_K+h, Bz_G, Bx_G, p, ref)
             - observables(p.T0_K-h, Bz_G, Bx_G, p, ref))/(2*h)
    lam = slope/f0
    return dict(nominal_Hz=f0, slope_Hz_K=slope, lambda_per_K=lam, reference=ref)


def composite_weights(lambda_D, lambda_Q):
    """L2026 Eq. (5): yC = wD*yD + wQ*yQ, wD+wQ=1."""
    if abs(lambda_D-lambda_Q) < 1e-12:
        raise ValueError("Temperature slopes are too similar for stable compensation.")
    wQ = lambda_D/(lambda_D-lambda_Q)
    return 1-wQ, wQ
