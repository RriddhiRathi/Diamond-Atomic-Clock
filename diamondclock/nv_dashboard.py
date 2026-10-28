"""Compact educational NV page, separate from all scientific experiment forms."""
import streamlit as st

from .nv_visualization import (ORIENTATION_LABELS, defect_cluster, magnetic_field,
                               field_metrics, crystal_figure)


def render_nv_demonstration():
    st.subheader('NV center in diamond')
    st.caption('IDEAL CRYSTAL GEOMETRY · Drag to rotate · Scroll to zoom · Use the toolbar to pan')
    main, side = st.columns([2.6, 1], gap='medium')
    with side:
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
        st.caption('20 G and 297 K are the aligned low-field starting example. Off-axis '
                   'settings here are geometry only; they do not configure the optical clock.')
        with st.expander('View options'):
            context = st.checkbox('Show full 3 × 3 × 3 crystal context', key='nv_context')
            bonds = st.checkbox('Show lattice bonds', value=True, key='nv_bonds')
            orientations = st.checkbox('Show four NV orientations', key='nv_orientations')
            atoms = st.checkbox('Atom labels', key='nv_atom_labels')
            bond_labels = st.checkbox('Bond labels', disabled=not bonds, key='nv_bond_labels')
        if st.button('Reset 3D view', key='reset_nv_camera'):
            st.session_state['nv_camera_revision'] = st.session_state.get('nv_camera_revision', 0) + 1
    with main:
        fig = crystal_figure(cluster, field, context=context, bonds=bonds,
            orientations=orientations, atom_labels=atoms, bond_labels=bond_labels,
            camera_revision=st.session_state.get('nv_camera_revision', 0))
        st.plotly_chart(fig, width='stretch', key='nv_crystal_plot',
            config=dict(scrollZoom=True, displaylogo=False, toImageButtonOptions=dict(filename='NV_crystal_ILLUSTRATION')))
        st.caption('Silver = carbon · Blue = nitrogen · Amber wire marker = one empty carbon site. '
                   'Teal = N → vacancy axis; yellow = B. Arrow lengths and atom radii are schematic. '
                   'When B is aligned, the arrows overlap along the same physical direction.')
    st.info('This is an educational crystal/vector illustration, not atomically resolved imaging '
            'or a quantum-dynamics result. Field/view changes do not run ODMR, fluorescence or clock simulations.')
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
