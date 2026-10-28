"""Ideal diamond geometry and Plotly illustration; no quantum/clock calculations.

Coordinates are Cartesian cubic coordinates in units of the conventional edge a.
See docs/NV_VISUALIZATION.md for the basis, polarity and rendering conventions.
"""
from dataclasses import dataclass
from itertools import product

import numpy as np
import plotly.graph_objects as go

from .odmr import ROTATIONS, spherical, transform, vector


FCC_BASIS = np.array([(0, 0, 0), (0, .5, .5), (.5, 0, .5), (.5, .5, 0)])
DIAMOND_BASIS = np.vstack((FCC_BASIS, FCC_BASIS + .25))
NEIGHBOR_DISTANCE = np.sqrt(3) / 4
DEFAULT_CAMERA = dict(eye=dict(x=1.65, y=1.45, z=1.1), up=dict(x=0, y=0, z=1))
ORIENTATION_LABELS = ('NV1 · [−1 1 1]', 'NV2 · [1 1 −1]',
                      'NV3 · [−1 −1 −1]', 'NV4 · [1 −1 1]')


@dataclass(frozen=True)
class NVCluster:
    sites: np.ndarray
    species: np.ndarray
    bonds: np.ndarray
    nitrogen_index: int
    vacancy: np.ndarray
    axis: np.ndarray
    orientation: int

    @property
    def nitrogen(self):
        return self.sites[self.nitrogen_index]


def diamond_lattice(cells=3):
    """Half-open cells [0,cells)^3; eight distinct sites per conventional cell."""
    if isinstance(cells, bool) or not isinstance(cells, (int, np.integer)) or not 1 <= cells <= 4:
        raise ValueError('Use 1..4 conventional cells along each edge.')
    return np.vstack([np.asarray(cell) + DIAMOND_BASIS
                      for cell in product(range(cells), repeat=3)])


def nearest_neighbor_bonds(sites):
    """Unique occupied-site pairs at sqrt(3)*a/4; no periodic boundary bonds."""
    sites = np.asarray(sites, dtype=float)
    if sites.ndim != 2 or sites.shape[1] != 3 or not np.all(np.isfinite(sites)):
        raise ValueError('Expected finite N by 3 lattice coordinates.')
    distance_squared = np.sum((sites[:, None] - sites[None, :]) ** 2, axis=2)
    return np.argwhere(np.triu(np.isclose(distance_squared, 3 / 16, rtol=0, atol=1e-12), 1))


def nv_axes():
    """The four directed local-z axes already used by the project's ODMR model."""
    return ROTATIONS[:, 2, :].copy()


def defect_cluster(orientation=0):
    """N at (5/4,5/4,5/4); remove its selected nearest FCC neighbor.

    With this B-sublattice N, each N->vacancy vector agrees with an existing NV
    frame's +z direction. Choosing another orientation moves only the one vacancy.
    """
    if isinstance(orientation, bool) or not isinstance(orientation, (int, np.integer)) or not 0 <= orientation < 4:
        raise ValueError('NV orientation must be 0..3.')
    pristine = diamond_lattice()
    nitrogen = np.full(3, 1.25)
    axis = nv_axes()[orientation]
    vacancy = nitrogen + np.rint(axis * np.sqrt(3)) / 4
    vacancy_index = np.flatnonzero(np.all(pristine == vacancy, axis=1)).item()
    sites = np.delete(pristine, vacancy_index, axis=0)
    nitrogen_index = np.flatnonzero(np.all(sites == nitrogen, axis=1)).item()
    species = np.full(len(sites), 'C')
    species[nitrogen_index] = 'N'
    return NVCluster(sites, species, nearest_neighbor_bonds(sites), nitrogen_index,
                     vacancy, axis, int(orientation))


def magnetic_field(magnitude_G=20., angle_deg=0., azimuth_deg=0., orientation=0):
    """Angles in the selected ODMR NV frame; return the lab-cubic B vector in G."""
    values = np.asarray([magnitude_G, angle_deg, azimuth_deg], dtype=float)
    if not np.all(np.isfinite(values)) or not 0 <= magnitude_G <= 50 or not 0 <= angle_deg <= 180 or not -180 <= azimuth_deg <= 180:
        raise ValueError('Use B=0..50 G, angle=0..180 degrees and azimuth=-180..180 degrees.')
    return transform(spherical(magnitude_G, angle_deg, azimuth_deg), orientation, inverse=True)


def field_metrics(field_G, axis):
    """Compute values from the same Cartesian vectors used to draw the arrows."""
    field, axis = vector(field_G), vector(axis)
    axis_norm = np.linalg.norm(axis)
    if axis_norm == 0:
        raise ValueError('The NV axis must be nonzero.')
    unit_axis = axis / axis_norm
    magnitude = float(np.linalg.norm(field))
    axial = float(field @ unit_axis)
    angle = None if magnitude == 0 else float(np.rad2deg(np.arccos(np.clip(axial / magnitude, -1, 1))))
    return dict(magnitude_G=magnitude, magnitude_T=magnitude * 1e-4,
                angle_deg=angle, axial_G=axial)


def _spheres(centres, radius, color, name, labels):
    """Batch actual low-poly sphere meshes into one trace for smooth interaction."""
    polar = np.linspace(0, np.pi, 9)
    azimuth = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    vertices = np.array([(np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t))
                         for t in polar for p in azimuth]) * radius
    faces = []
    for row in range(8):
        for col in range(12):
            a, b = row * 12 + col, row * 12 + (col + 1) % 12
            faces.extend(((a, a + 12, b), (b, a + 12, b + 12)))
    faces = np.asarray(faces)
    xyz = np.concatenate([vertices + centre for centre in centres])
    triangles = np.concatenate([faces + k * len(vertices) for k in range(len(centres))])
    return go.Mesh3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2],
        i=triangles[:, 0], j=triangles[:, 1], k=triangles[:, 2],
        color=color, name=name, text=np.repeat(labels, len(vertices)),
        hovertemplate='%{text}<extra></extra>', showlegend=True,
        lighting=dict(ambient=.55, diffuse=.75, specular=.2, roughness=.8),
        lightposition=dict(x=4, y=4, z=6))


def _arrow(fig, origin, direction, color, name, length=1.05, width=7):
    unit = direction / np.linalg.norm(direction)
    tip = origin + length * unit
    fig.add_trace(go.Scatter3d(x=[origin[0], tip[0]], y=[origin[1], tip[1]],
        z=[origin[2], tip[2]], mode='lines', line=dict(color=color, width=width),
        name=name, hovertemplate=name + '<extra></extra>'))
    fig.add_trace(go.Cone(x=[tip[0]], y=[tip[1]], z=[tip[2]],
        u=[unit[0]], v=[unit[1]], w=[unit[2]],
        anchor='tip', sizemode='absolute', sizeref=.16,
        colorscale=[[0, color], [1, color]], showscale=False,
        showlegend=False, hoverinfo='skip'))


def crystal_figure(cluster, field_G, *, context=False, bonds=True, orientations=False,
                   atom_labels=False, bond_labels=False, camera_revision=0):
    """Educational geometry in (r-r_N)/a; arrows have schematic lengths."""
    field = vector(field_G)
    positions = cluster.sites - cluster.nitrogen
    vacancy = cluster.vacancy - cluster.nitrogen
    visible = np.ones(len(positions), dtype=bool) if context else np.linalg.norm(positions, axis=1) <= 1.05
    indices = np.flatnonzero(visible)
    fig = go.Figure()
    if bonds:
        edges = cluster.bonds[visible[cluster.bonds].all(axis=1)]
        segments = np.full((len(edges), 3, 3), np.nan)
        segments[:, :2] = positions[edges]
        xyz = segments.reshape(-1, 3)
        fig.add_trace(go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode='lines',
            line=dict(color='#78899b', width=3), opacity=.8, name='Nearest-neighbor bonds', hoverinfo='skip'))
        if bond_labels:
            mid = positions[edges].mean(axis=1)
            fig.add_trace(go.Scatter3d(x=mid[:, 0], y=mid[:, 1], z=mid[:, 2], mode='text',
                text=['√3 a/4'] * len(mid), textfont=dict(size=10, color='#adb9c8'),
                name='Bond lengths (ideal)', showlegend=False, hoverinfo='skip'))
    carbon = indices[cluster.species[indices] == 'C']
    labels = [f'C{i} · cubic r/a = ({cluster.sites[i, 0]:g}, {cluster.sites[i, 1]:g}, {cluster.sites[i, 2]:g})' for i in carbon]
    fig.add_trace(_spheres(positions[carbon], .06, '#aebbc9', 'Carbon', labels))
    fig.add_trace(_spheres(np.zeros((1, 3)), .095, '#3db8ff', 'Nitrogen (substitution)',
                          ['N · substitutes one carbon site']))
    # Three wire circles mark an EMPTY site. No atom mesh or chemical bond there.
    ring = np.linspace(0, 2 * np.pi, 65)
    for plane in range(3):
        xyz = np.zeros((len(ring), 3))
        xyz[:, plane] = .105 * np.cos(ring)
        xyz[:, (plane + 1) % 3] = .105 * np.sin(ring)
        xyz += vacancy
        fig.add_trace(go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode='lines',
            line=dict(color='#ffb454', width=4), name='Vacancy (empty site)',
            showlegend=plane == 0, hovertemplate='V · missing carbon, not an atom<extra></extra>'))
    fig.add_trace(go.Scatter3d(x=[0, vacancy[0]], y=[0, vacancy[1]], z=[.16, vacancy[2] + .16],
        mode='text', text=['N', 'V · empty'], textfont=dict(color='#edf4ff', size=14),
        showlegend=False, hoverinfo='skip'))
    if atom_labels:
        pts = positions[carbon] + [0, 0, .1]
        fig.add_trace(go.Scatter3d(x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode='text',
            text=[f'C{i}' for i in carbon], textfont=dict(size=10), showlegend=False, hoverinfo='skip'))
    if orientations:
        for k, axis in enumerate(nv_axes()):
            if k == cluster.orientation:
                continue
            tip = axis * 1.05
            fig.add_trace(go.Scatter3d(x=[0, tip[0]], y=[0, tip[1]], z=[0, tip[2]],
                mode='lines', line=dict(color='#be9de8', width=3, dash='dash'), opacity=.65,
                name='Other NV orientations', showlegend=k == next(j for j in range(4) if j != cluster.orientation),
                hovertemplate=ORIENTATION_LABELS[k] + '<extra>Alternative orientation, not another defect</extra>'))
    _arrow(fig, np.zeros(3), cluster.axis, '#30d5c8', 'Selected NV axis · N → V', width=9)
    if np.linalg.norm(field) > 0:
        _arrow(fig, np.zeros(3), field, '#f8d16b', 'B · external field', length=1.25, width=4)
    metrics = field_metrics(field, cluster.axis)
    bounds = [-1.45, 1.75] if context else [-1.35, 1.35]
    axis = dict(range=bounds, showbackground=False, gridcolor='#263448',
                zerolinecolor='#53657a', tickfont=dict(size=10), nticks=5)
    fig.update_layout(template='plotly_dark', height=610, margin=dict(l=0, r=0, t=4, b=0),
        paper_bgcolor='#080b10', scene=dict(bgcolor='#080b10', aspectmode='cube',
            xaxis=dict(axis, title='[100] · Δx/a'), yaxis=dict(axis, title='[010] · Δy/a'),
            zaxis=dict(axis, title='[001] · Δz/a'), camera=DEFAULT_CAMERA,
            uirevision=f'nv-camera-{camera_revision}', dragmode='orbit'),
        legend=dict(orientation='h', yanchor='top', y=-.01, x=0, font=dict(size=11)),
        meta=dict(illustration='Ideal crystal geometry; no quantum simulation',
                  occupied_sites=len(cluster.sites), visible_atoms=int(visible.sum()),
                  vacancy_count=1, field_G=field.tolist(), **metrics))
    return fig
