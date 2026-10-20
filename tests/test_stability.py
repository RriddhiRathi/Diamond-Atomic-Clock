import numpy as np
import pytest
from diamondclock.stability import overlapping_adev


def test_nist_nine_point_dataset():
    # NIST SP1065 Tables 29-30, printed pp.106-107.
    y=np.array([892,809,823,798,671,644,883,903,677],float)
    a=overlapping_adev(y,factors=[1,2])
    np.testing.assert_allclose(a.adev,[91.22945,85.95287],atol=1e-5,rtol=0)


def test_independent_allantools():
    import allantools
    y=np.random.default_rng(4).normal(0,1e-9,8192)
    ms=np.array([1,2,7,32,128,512])
    a=overlapping_adev(y,.5,ms)
    tau,value,_,pairs=allantools.oadev(y,rate=2.,data_type='freq',taus=ms*.5)
    np.testing.assert_allclose(a.adev,value,rtol=1e-11)
    np.testing.assert_array_equal(a.overlapping_pairs,pairs)


def test_white_fm_scaling_and_linear_drift():
    y=np.random.default_rng(42).normal(0,2e-9,131072)
    a=overlapping_adev(y,factors=[1,4,16,64])
    np.testing.assert_allclose(a.adev,2e-9/np.sqrt(a.m),rtol=.04)
    t=np.arange(10000)*.5
    slope=3e-12
    d=overlapping_adev(2e-6+slope*t,.5,[1,7,100])
    np.testing.assert_allclose(d.adev,slope*d.tau_s/np.sqrt(2),rtol=1e-8)


def test_constant_and_invalid_data():
    assert overlapping_adev(np.ones(100),factors=[1,10]).adev.max()==0
    for y,dt in [(np.array([1.,np.nan]),1),(np.ones(10),0),(np.ones((2,2)),1)]:
        with pytest.raises(ValueError):overlapping_adev(y,dt,factors=[1])
