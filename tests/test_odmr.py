"""Analytic/unit/invariance checks for the new spectroscopy extension."""
from dataclasses import replace
import numpy as np
import pytest
from diamondclock import odmr as o
from diamondclock.physics import Physics, hamiltonian


def uncoupled():
    return replace(Physics(),Q0_Hz=0,Apar0_Hz=0,Aperp0_Hz=0,gamma_n_Hz_G=0)


def test_rotations_units_and_coordinate_roundtrips():
    np.testing.assert_allclose(o.ROTATIONS@o.ROTATIONS.transpose(0,2,1),np.tile(np.eye(3),(4,1,1)),atol=1e-15)
    np.testing.assert_allclose(np.linalg.det(o.ROTATIONS),1)
    dots=o.ROTATIONS[:,2]@o.ROTATIONS[:,2].T
    np.testing.assert_allclose(dots,np.eye(4)*4/3-np.ones((4,4))/3,atol=1e-15)
    for k in range(4):
        np.testing.assert_allclose(o.transform(o.transform([3,-2,1],k),k,inverse=True),[3,-2,1],atol=1e-14)
    np.testing.assert_allclose(o.spherical(10,90,0),[10,0,0],atol=1e-14)
    assert o.Stark().d_perp_Hz_m_V*100==17
    assert o.Stark().d_parallel_Hz_m_V*100==pytest.approx(.35)


def test_existing_hamiltonian_overlap_hermiticity_and_y_rotation():
    for bx,bz in [(0,475),(.3,470),(.1,18)]:
        actual=o.spectroscopy_hamiltonian(298,[bx,0,bz])
        np.testing.assert_allclose(actual,hamiltonian(298,bz,bx),atol=0,rtol=0)
    h=o.spectroscopy_hamiltonian(297,[2,3,20],[100,200,300])
    np.testing.assert_allclose(h,h.conj().T,atol=1e-12)
    # At E=0, spectrum is axially invariant when rotating transverse B about z.
    ex=np.linalg.eigvalsh(o.spectroscopy_hamiltonian(297,[2,0,20]))
    ey=np.linalg.eigvalsh(o.spectroscopy_hamiltonian(297,[0,2,20]))
    np.testing.assert_allclose(ex,ey,atol=1e-5,rtol=0)


def test_analytic_zeeman_stark_splitting_and_selection_rules():
    p=uncoupled(); b=18.; ez=1e5; ex=2e5; ey=3e5
    h=o.spectroscopy_hamiltonian(297,[0,0,b],[ex,ey,ez],p)
    e=np.linalg.eigvalsh(h)
    centre=p.D0_Hz+o.Stark().d_parallel_Hz_m_V*ez
    split=np.sqrt((p.gamma_e_Hz_G*b)**2+o.Stark().d_perp_Hz_m_V**2*(ex**2+ey**2))
    np.testing.assert_allclose(e,[0]*3+[centre-split]*3+[centre+split]*3,atol=1e-5,rtol=0)
    h=o.spectroscopy_hamiltonian(297,[0,0,b],p=p)
    x=o.transition_table(h,[1,0,0],p)
    active=x[x.dip_weight>1e-10]
    np.testing.assert_allclose(active.frequency_Hz,[p.D0_Hz-p.gamma_e_Hz_G*b,p.D0_Hz+p.gamma_e_Hz_G*b],atol=1e-5,rtol=0)
    np.testing.assert_allclose(active.dip_weight,[.5,.5],atol=1e-12)
    z=o.transition_table(h,[0,0,1],p)
    assert z.dip_weight.max()<1e-20
    assert (x.frequency_Hz>0).all()  # no self-transitions


def test_complex_eigenvectors_degenerate_manifolds_are_basis_invariant(monkeypatch):
    p=uncoupled()
    h=o.spectroscopy_hamiltonian(297,[0,0,18],p=p)
    expected=o.transition_table(h,[1,1,0],p)
    e,v=np.linalg.eigh(h)
    rng=np.random.default_rng(17)
    for group in o._groups(e):
        u,_=np.linalg.qr(rng.normal(size=(len(group),len(group)))+1j*rng.normal(size=(len(group),len(group))))
        v[:,group]=v[:,group]@u
    monkeypatch.setattr(np.linalg,'eigh',lambda _: (e,v))
    actual=o.transition_table(h,[1,1,0],p)
    np.testing.assert_allclose(actual.strength,expected.strength,atol=1e-12)
    np.testing.assert_allclose(actual.dip_weight,expected.dip_weight,atol=1e-12)


def test_lorentzian_fwhm_ensemble_weights_and_exact_grid():
    np.testing.assert_allclose(o.lorentzian(np.array([-5.,0.,5.]),0,10),[.5,1,.5])
    c=o.ODMRConfig(points=1001,weights=(1,0,0,0))
    s,lines,levels=o.spectrum(c)
    assert len(s)==1001 and len(levels)==36
    assert s.frequency_Hz.iloc[0]==c.start_Hz and s.frequency_Hz.iloc[-1]==c.stop_Hz
    np.testing.assert_array_equal(s.combined_fluorescence,s.NV1_fluorescence)
    equal,_,_=o.spectrum(replace(c,weights=(1,1,1,1)))
    np.testing.assert_allclose(equal.combined_fluorescence,equal[[f'NV{k}_fluorescence' for k in range(1,5)]].mean(axis=1))
    no_contrast,_,_=o.spectrum(replace(c,contrast=0))
    np.testing.assert_array_equal(no_contrast.combined_fluorescence,np.ones(c.points))
    # Hyperfine is enabled: more than two active electronic lines per orientation.
    assert len(lines[(lines.orientation==1)&(lines.frequency_Hz>1e8)&(lines.dip_weight>1e-4)])>=6


def test_hellmann_feynman_matches_finite_differences():
    b=np.array([.3,.2,475.]);step=.001
    t=o.transition_sensitivities(297,b)
    for k,label in enumerate(('x','y','z')):
        delta=np.eye(3)[k]*step
        plus=np.linalg.eigvalsh(o.spectroscopy_hamiltonian(297,b+delta))
        minus=np.linalg.eigvalsh(o.spectroscopy_hamiltonian(297,b-delta))
        gradient=(plus-minus)/(2*step)
        expected=[gradient[r.final_rank]-gradient[r.initial_rank] for r in t.itertuples()]
        np.testing.assert_allclose(t[f'dnu_dB{label}_Hz_G'],expected,atol=.01,rtol=1e-5)
    p=uncoupled()
    deg=o.transition_sensitivities(297,[0,0,0],p=p)
    assert deg.dnu_dBz_Hz_G.isna().all()


@pytest.mark.parametrize('changes',[{'linewidth_Hz':0},{'weights':(0,0,0,0)},
    {'points':100},{'start_Hz':4e9},{'microwave_lab':(0,0,0)},
    {'B_lab_G':(np.nan,0,0)},{'temperature_K':310}])
def test_invalid_spectroscopy_input(changes):
    with pytest.raises(ValueError):o.spectrum(replace(o.ODMRConfig(),**changes))


def test_stark_scope_and_vector_rejection():
    with pytest.raises(ValueError):o.spectroscopy_hamiltonian(297,[0,0,0],[1e10,0,0])
    with pytest.raises(ValueError):o.transform([1,2],0)
    with pytest.raises(ValueError):o.transform([1,2,3],4)
