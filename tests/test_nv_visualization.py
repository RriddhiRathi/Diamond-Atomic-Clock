"""Crystallographic and field-vector invariants, independent of quantum solvers."""
import numpy as np
import pytest

from diamondclock.nv_visualization import (diamond_lattice, nearest_neighbor_bonds,
    defect_cluster, nv_axes, magnetic_field, field_metrics, crystal_figure, DEFAULT_CAMERA)


def test_conventional_basis_counts_and_translations():
    expected = {(0, 0, 0), (0, .5, .5), (.5, 0, .5), (.5, .5, 0),
                (.25, .25, .25), (.25, .75, .75), (.75, .25, .75), (.75, .75, .25)}
    assert set(map(tuple, diamond_lattice(1))) == expected
    sites = diamond_lattice(3)
    assert len(sites) == len(set(map(tuple, sites))) == 216
    assert set(map(tuple, sites % 1)) == expected
    assert np.all((sites >= 0) & (sites < 3))
    assert np.array_equal(sites, diamond_lattice(3))


def test_nearest_neighbor_distance_and_tetrahedral_coordination():
    sites = diamond_lattice()
    bonds = nearest_neighbor_bonds(sites)
    assert np.all(bonds[:, 0] < bonds[:, 1])
    assert len(set(map(tuple, bonds))) == len(bonds)
    assert np.allclose(np.linalg.norm(sites[bonds[:, 0]] - sites[bonds[:, 1]], axis=1), np.sqrt(3) / 4)
    # Compare against all pairs: no skipped nearest bonds or periodic wraparound.
    distance = np.linalg.norm(sites[:, None] - sites[None, :], axis=2)
    assert set(map(tuple, bonds)) == set(map(tuple, np.argwhere(np.triu(np.isclose(distance, np.sqrt(3) / 4), 1))))
    central = np.flatnonzero(np.all(sites == [1.25, 1.25, 1.25], axis=1)).item()
    neighbors = np.flatnonzero(np.isclose(distance[central], np.sqrt(3) / 4))
    assert len(neighbors) == 4
    unit = (sites[neighbors] - sites[central]) / (np.sqrt(3) / 4)
    assert np.allclose((unit @ unit.T)[~np.eye(4, dtype=bool)], -1 / 3)
    assert np.bincount(bonds.ravel()).max() == 4


@pytest.mark.parametrize('orientation', range(4))
def test_exactly_one_substitution_one_vacancy_and_valid_axis(orientation):
    from diamondclock.odmr import ROTATIONS

    pristine = set(map(tuple, diamond_lattice()))
    cluster = defect_cluster(orientation)
    occupied = set(map(tuple, cluster.sites))
    assert len(cluster.sites) == 215
    assert pristine - occupied == {tuple(cluster.vacancy)}
    assert not occupied - pristine
    assert np.count_nonzero(cluster.species == 'N') == 1
    assert np.count_nonzero(cluster.species == 'C') == 214
    assert np.array_equal(cluster.nitrogen, [1.25, 1.25, 1.25])
    nv = cluster.vacancy - cluster.nitrogen
    assert np.isclose(np.linalg.norm(nv), np.sqrt(3) / 4)
    assert np.allclose(nv / np.linalg.norm(nv), ROTATIONS[orientation, 2])
    assert np.allclose(cluster.axis, nv_axes()[orientation])
    assert np.count_nonzero(cluster.bonds == cluster.nitrogen_index) == 3
    assert not np.any(np.all(cluster.sites == cluster.vacancy, axis=1))
    # No atom or chemical bond may be present at the missing site.
    assert np.allclose(np.linalg.norm(cluster.sites[cluster.bonds[:, 0]] - cluster.sites[cluster.bonds[:, 1]], axis=1), np.sqrt(3) / 4)


def test_four_crystallographically_valid_axes_match_the_project_frames():
    axes = nv_axes()
    assert set(map(tuple, np.rint(axes * np.sqrt(3)).astype(int))) == {
        (-1, 1, 1), (1, 1, -1), (-1, -1, -1), (1, -1, 1)}
    assert np.allclose(np.linalg.norm(axes, axis=1), 1)
    assert np.allclose((axes @ axes.T)[~np.eye(4, dtype=bool)], -1 / 3)


@pytest.mark.parametrize('orientation', range(4))
@pytest.mark.parametrize('angle', [0., 37., 90., 180.])
def test_field_vector_angle_projection_and_units(orientation, angle):
    from diamondclock.odmr import transform

    field = magnetic_field(20., angle, 63., orientation)
    metrics = field_metrics(field, nv_axes()[orientation])
    assert metrics['magnitude_G'] == pytest.approx(20.)
    assert metrics['magnitude_T'] == pytest.approx(.002)
    assert metrics['angle_deg'] == pytest.approx(angle, abs=2e-6)
    assert metrics['axial_G'] == pytest.approx(20 * np.cos(np.deg2rad(angle)), abs=1e-12)
    assert transform(field, orientation)[2] == pytest.approx(metrics['axial_G'], abs=1e-12)


def test_zero_field_has_no_angle_or_field_arrow():
    cluster = defect_cluster()
    field = magnetic_field(0., 90., 45.)
    assert field_metrics(field, cluster.axis) == dict(magnitude_G=0., magnitude_T=0., angle_deg=None, axial_G=0.)
    figure = crystal_figure(cluster, field)
    assert not any(trace.name == 'B · external field' for trace in figure.data)


def test_figure_is_deterministic_and_draws_the_measured_vector_directions():
    cluster = defect_cluster(2)
    field = magnetic_field(20., 45., -30., 2)
    figure = crystal_figure(cluster, field, orientations=True)
    assert figure.to_json() == crystal_figure(defect_cluster(2), field, orientations=True).to_json()
    assert figure.layout.meta['vacancy_count'] == 1
    assert figure.layout.meta['occupied_sites'] == 215
    assert 5 < figure.layout.meta['visible_atoms'] < 215
    for name, expected in [('B · external field', field / np.linalg.norm(field)),
                           ('Selected NV axis · N → V', cluster.axis)]:
        trace = next(t for t in figure.data if t.name == name)
        tip = np.array([trace.x[-1], trace.y[-1], trace.z[-1]])
        assert np.allclose(tip / np.linalg.norm(tip), expected)
    assert len([t for t in figure.data if t.type == 'mesh3d']) == 2
    assert len([t for t in figure.data if t.name == 'Vacancy (empty site)']) == 3
    assert len([t for t in figure.data if t.name == 'Other NV orientations']) == 3
    full = crystal_figure(cluster, field, context=True, bonds=False, atom_labels=True)
    assert full.layout.meta['visible_atoms'] == 215
    assert not any(t.name == 'Nearest-neighbor bonds' for t in full.data)
    reset = crystal_figure(cluster, field, camera_revision=1)
    assert figure.layout.scene.camera.to_plotly_json() == DEFAULT_CAMERA
    assert reset.layout.scene.uirevision != figure.layout.scene.uirevision
    assert reset.layout.scene.camera == figure.layout.scene.camera


@pytest.mark.parametrize('operation', [lambda: diamond_lattice(5), lambda: defect_cluster(4),
    lambda: magnetic_field(475), lambda: magnetic_field(20, -1),
    lambda: field_metrics([1, 2, np.nan], [1, 0, 0]),
    lambda: field_metrics([1, 0, 0], [0, 0, 0])])
def test_reject_invalid_geometry_inputs(operation):
    with pytest.raises(ValueError):
        operation()
