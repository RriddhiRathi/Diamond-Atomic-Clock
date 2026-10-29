"""Validate the recovered presentation adapter against the unchanged engine."""
import numpy as np
import pandas as pd
import pytest
from diamondclock import nv_spectroscopy as demo
from diamondclock.odmr import ODMRConfig, spectrum, transform
from diamondclock.nv_visualization import magnetic_field, defect_cluster, crystal_figure
from diamondclock.run_provenance import source_fingerprint, validate


@pytest.mark.parametrize('orientation', range(4))
def test_adapter_matches_existing_engine_and_displayed_field(orientation):
    field = magnetic_field(20, 37, 41, orientation)
    data, lines, config, context = demo.cached_spectrum(tuple(field), orientation, source_fingerprint())
    expected, expected_lines, _ = spectrum(ODMRConfig(**config))
    pd.testing.assert_frame_equal(data, expected)
    pd.testing.assert_frame_equal(lines, expected_lines)
    assert np.array_equal(config['B_lab_G'], field)
    assert np.allclose(transform(config['microwave_lab'], orientation), [1, 0, 0])
    assert np.allclose(data.combined_fluorescence, data[f'NV{orientation+1}_fluorescence'])
    geometry = crystal_figure(defect_cluster(orientation), field)
    assert np.allclose(geometry.layout.meta['field_G'], config['B_lab_G'])
    assert context['config'] == config
    validate(context)
    again = demo.cached_spectrum(tuple(field), orientation, source_fingerprint())
    pd.testing.assert_frame_equal(data, again[0])


def test_frequency_interpolation_boundaries_units_and_transition_markers():
    data, lines, config, _ = demo.cached_spectrum(tuple(magnetic_field()), 0, source_fingerprint())
    index = int(data.combined_fluorescence.idxmin())
    first, second = data.iloc[index:index+2].itertuples(index=False)
    frequency = (first.frequency_Hz + second.frequency_Hz)/2
    expected = (data.combined_fluorescence.iloc[index] + data.combined_fluorescence.iloc[index+1])/2
    assert demo.fluorescence(data, frequency) == pytest.approx(expected)
    for edge in (data.frequency_Hz.iloc[0], data.frequency_Hz.iloc[-1]):
        assert demo.fluorescence(data, edge/1e9*1e9) == pytest.approx(demo.fluorescence(data, edge))
    with pytest.raises(ValueError):
        demo.fluorescence(data, data.frequency_Hz.iloc[-1]+1)
    fig = demo.spectrum_figure(data, lines, config, 0, frequency)
    assert fig.layout.xaxis.title.text == 'Microwave frequency (GHz)'
    assert fig.layout.shapes[0].x0 == pytest.approx(frequency/1e9)
    point = next(t for t in fig.data if t.name == 'Selected proxy')
    assert point.x[0] == pytest.approx(frequency/1e9)
    assert point.y[0] == pytest.approx(expected)
    ticks = next(t for t in fig.data if t.name.startswith('Calculated transition'))
    active = lines[(lines.orientation==1)&(lines.dip_weight>1e-8)&lines.frequency_Hz.between(config['start_Hz'],config['stop_Hz'])]
    assert np.allclose(ticks.x, active.frequency_Hz/1e9)
    assert data.combined_fluorescence.min() < data.combined_fluorescence.iloc[0]


def test_zero_field_and_field_dependent_resonances():
    zero, lines0, _, _ = demo.cached_spectrum((0.,0.,0.), 0, source_fingerprint())
    data, lines20, _, _ = demo.cached_spectrum(tuple(magnetic_field()), 0, source_fingerprint())
    assert np.all(np.isfinite(zero.combined_fluorescence))
    assert zero.combined_fluorescence.min() < 1
    assert not lines0.frequency_Hz.equals(lines20.frequency_Hz)
    f = float(zero.frequency_Hz.iloc[0])
    assert demo.fluorescence(zero, f) == pytest.approx(zero.combined_fluorescence.iloc[0])


@pytest.mark.parametrize('states', [7,21])
@pytest.mark.parametrize('magnitude,angle,supported', [(20,0,True),(50,0,True),(20,30,False),(0,0,False),(20,180,False)])
def test_separate_optical_domain_is_explicit(states, magnitude, angle, supported):
    for k in range(4):
        valid, note = demo.optical_scope(magnetic_field(magnitude,angle,0,k), k, states)
        assert valid is supported
        assert note


def test_laser_and_microwave_states_are_not_photon_counts():
    assert demo.emission_signal(.98, True, True) == .98
    assert demo.emission_signal(.98, True, False) == 1.
    assert demo.emission_signal(.98, False, True) is None


def test_schematic_overlays_follow_signal_and_can_be_hidden():
    from diamondclock.nv_visualization import measurement_overlays
    cluster = defect_cluster()
    field = magnetic_field()
    fig = crystal_figure(cluster, field, show_field=False)
    assert not any(t.name == 'B · external field' for t in fig.data)
    count = len(fig.data)
    measurement_overlays(fig, cluster, signal=.98, enabled=False)
    assert len(fig.data) == count
    measurement_overlays(fig, cluster, signal=.98)
    emission = next(t for t in fig.data if t.name == 'Schematic fluorescence · scaled proxy')
    assert emission.opacity == .98
    assert any(t.name == 'Schematic optical excitation' for t in fig.data)
    assert any(t.name == 'Schematic microwave drive' for t in fig.data)
    off = crystal_figure(cluster, field)
    measurement_overlays(off, cluster, laser=False, microwave=False)
    assert not any((t.name or '').startswith('Schematic') for t in off.data)
