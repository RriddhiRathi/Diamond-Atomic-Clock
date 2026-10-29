"""Compact educational NV page, separate from all scientific experiment forms."""
import streamlit as st

from .plot_style import crystal_style
from .nv_visualization import (ORIENTATION_LABELS, defect_cluster, magnetic_field,
                               field_metrics, crystal_figure, measurement_overlays)


def render_nv_demonstration():
    st.title('NV-Center & ODMR')
    st.caption('Crystal geometry → microwave resonance → normalized fluorescence · educational illustration and simulation')
    with st.expander('Field and geometry controls'):
        orientation = st.selectbox('Selected NV orientation', range(4),
            format_func=lambda k: ORIENTATION_LABELS[k], key='nv_orientation')
        a,b,c=st.columns(3)
        magnitude = a.slider('Field magnitude (G)', 0., 50., 20., .5, key='nv_field')
        angle = b.slider('B angle to selected NV (°)', 0., 180., 0., 1., key='nv_angle')
        azimuth = c.slider('Azimuth around selected NV (°)', -180., 180., 0., 1., key='nv_azimuth')
        cluster = defect_cluster(orientation)
        field = magnetic_field(magnitude, angle, azimuth, orientation)
        metrics = field_metrics(field, cluster.axis)
        st.markdown('**Displayed field geometry**')
        st.write(f"|B| = {metrics['magnitude_G']:g} G = {metrics['magnitude_T']:.4g} T")
        st.write('Angle = undefined at zero field' if metrics['angle_deg'] is None
                 else f"Angle(B, NV) = {metrics['angle_deg']:.1f}°")
        st.write(f"Axial B∥ = {metrics['axial_G']:.3f} G")
        st.caption('20 G and 297 K are the aligned low-field starting example. Field settings update '
                   'the primary ODMR proxy; they do not configure the separate optical clock.')
    with st.expander('3D view & overlays'):
        with st.container():
            overlays = st.checkbox('Show educational overlays', True, key='nv_overlays')
            st.checkbox('Show other NV spectra', key='nv_other_spectra')
            show_field = st.checkbox('Show magnetic-field arrow', True, key='nv_show_field')
            context = st.checkbox('Show full 3 × 3 × 3 crystal context', key='nv_context')
            bonds = st.checkbox('Show lattice bonds', value=True, key='nv_bonds')
            orientations = st.checkbox('Show four NV orientations', key='nv_orientations')
            atoms = st.checkbox('Atom labels', key='nv_atom_labels')
            bond_labels = st.checkbox('Bond labels', disabled=not bonds, key='nv_bond_labels')
        if st.button('Reset 3D view', key='reset_nv_camera'):
            st.session_state['nv_camera_revision'] = st.session_state.get('nv_camera_revision', 0) + 1
    main, side = st.columns([1, 1], gap='medium')
    with side:
        from .nv_spectroscopy import render_spectrum
        laser, microwave, signal = render_spectrum(field, orientation)
    with main:
        fig = crystal_figure(cluster, field, context=context, bonds=bonds,
            orientations=orientations, atom_labels=atoms, bond_labels=bond_labels,
            camera_revision=st.session_state.get('nv_camera_revision', 0), show_field=show_field)
        measurement_overlays(fig, cluster, laser=laser, microwave=microwave,
                             signal=signal, enabled=overlays)
        st.markdown('**Diamond crystal · N–V defect**')
        crystal_style(fig)
        st.plotly_chart(fig, width='stretch', key='nv_crystal_plot',
            config=dict(scrollZoom=True, displaylogo=False, toImageButtonOptions=dict(filename='NV_crystal_ILLUSTRATION')))
        st.caption('Silver = carbon · Blue = nitrogen · Amber wire marker = one empty carbon site. '
                   'Teal = N → vacancy axis; yellow = B. Arrow lengths and atom radii are schematic. '
                   'When B is aligned, the arrows overlap along the same physical direction.')
    st.caption('Physical crystal geometry; optical/MW arrows are schematic. The ODMR curve is simulated, not measured. An ODMR dip does not establish clock lock.')
    with st.expander('NV spin, optical readout & model limits'):
        st.write('One substitutional nitrogen and one adjacent vacancy define the directed ⟨111⟩ axis. '
                 'The NV⁻ electronic ground spin has S=1 with zero-field splitting D ≈ 2.87 GHz. '
                 'Magnetic-field orientation changes the axial and transverse Hamiltonian terms. [L2023, D2012]')
        st.write('Optical preparation/readout and microwave driving enable ODMR. This display uses the '
                 'phenomenological transition-strength proxy, not optical-cycle populations or measured '
                 'photon counts. The seven/21-state models remain in Research Tools → Optical measurement. '
                 'Clock lock, time error and Allan deviation are evaluated separately. [TET2012, DRE2011]')
        st.caption('View/frequency changes do not run optical-cycle or clock simulations. Static arrows are '
                   'educational schematics, not electromagnetic propagation or photon trajectories. '
                   'This finite ideal cluster is not atomically resolved experimental imaging.')
    with st.expander('Crystal construction, conventions and sources'):
        from .resources import project_root

        st.markdown((project_root() / 'references/nv_visualization_map.md').read_text(encoding='utf-8'))
        st.markdown((project_root() / 'references/nv_odmr_demo_map.md').read_text(encoding='utf-8'))
