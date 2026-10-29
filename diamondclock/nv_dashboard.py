"""Compact educational NV page, separate from all scientific experiment forms."""
import streamlit as st

from .nv_visualization import (ORIENTATION_LABELS, defect_cluster, magnetic_field,
                               field_metrics, crystal_figure, measurement_overlays)


def render_nv_demonstration():
    st.subheader('NV center in diamond')
    st.caption('CRYSTAL ILLUSTRATION + SIMULATED ODMR · Optical preparation → microwave resonance → fluorescence readout')
    with st.expander('Field and geometry controls'):
        orientation = st.selectbox('Selected NV orientation', range(4),
            format_func=lambda k: ORIENTATION_LABELS[k], key='nv_orientation')
        magnitude = st.slider('Field magnitude (G)', 0., 50., 20., .5, key='nv_field')
        angle = st.slider('B angle to selected NV (°)', 0., 180., 0., 1., key='nv_angle')
        azimuth = st.slider('Azimuth around selected NV (°)', -180., 180., 0., 1., key='nv_azimuth')
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
        st.markdown('**View options**')
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
        fig.update_layout(height=490)
        st.plotly_chart(fig, width='stretch', key='nv_crystal_plot',
            config=dict(scrollZoom=True, displaylogo=False, toImageButtonOptions=dict(filename='NV_crystal_ILLUSTRATION')))
        st.caption('Silver = carbon · Blue = nitrogen · Amber wire marker = one empty carbon site. '
                   'Teal = N → vacancy axis; yellow = B. Arrow lengths and atom radii are schematic. '
                   'When B is aligned, the arrows overlap along the same physical direction.')
    st.info('This is an educational crystal/vector illustration, not atomically resolved imaging '
            'or a quantum-dynamics result. Field changes update the cached ODMR proxy. View/frequency changes do not run optical-cycle or clock simulations. Arrows are static schematics, not electromagnetic propagation or photon trajectories.')
    with st.expander('How the measurement works'):
        st.write('Optical excitation prepares and reads out the NV spin. Microwave-driven spin transitions reduce '
                 'fluorescence through spin-dependent optical pathways. Here the decrease is a phenomenological '
                 'ODMR proxy, not a calculated optical-cycle population. Resonance identification can inform a '
                 'frequency reference; feedback, clock time error and Allan deviation must be tested separately '
                 'in Clock Performance. [L2023, D2012, TET2012, DRE2011]')
    a, b, c = st.columns(3)
    with a:
        st.markdown('**One local point defect**')
        st.write('Nitrogen replaces one carbon; an adjacent carbon is absent. The selected pair '
                 'defines one directed ⟨111⟩ axis. Other axis overlays represent alternatives, not extra vacancies.')
    with b:
        st.markdown('**Spin resonance**')
        st.write('The NV⁻ ground electronic spin has S=1. Zero-field splitting D ≈ 2.87 GHz '
                 'separates mₛ=0 and mₛ=±1. Magnetic-field orientation changes axial and transverse '
                 'components in the spin Hamiltonian. [L2023, D2012]')
    with c:
        st.markdown('**From spins to ODMR**')
        st.write('Optical preparation/readout and microwave driving produce spin-dependent '
                 'fluorescence. An ODMR scan detects this response versus microwave frequency. '
                 'The implemented solvers remain in Advanced Research. [TET2012, DRE2011]')
    with st.expander('Crystal construction, conventions and sources'):
        from .resources import project_root

        st.markdown((project_root() / 'references/nv_visualization_map.md').read_text(encoding='utf-8'))
        st.markdown((project_root() / 'references/nv_odmr_demo_map.md').read_text(encoding='utf-8'))
