"""Direct reference and export pages. No scientific calculations are launched here."""
from dataclasses import asdict
import hashlib
import json
import sqlite3

import pandas as pd
import streamlit as st

from .reference_store import ReferenceStore, verification_label, catalog_bytes, bibtex_bytes
from .reporting import ROOT, sources, provenance, benchmarks, zip_files
from .simulation import Config
from .run_provenance import source_fingerprint, validate, verify_files

MAPS = {'Stability & compensation':'equation_map.md', 'ODMR spectroscopy':'odmr_equation_map.md',
        'Optical readout':'optical_equation_map.md', 'Oscillator & feedback':'clock_equation_map.md',
        'NV crystal geometry':'nv_visualization_map.md', 'Interactive ODMR':'nv_odmr_demo_map.md'}
DOCUMENTS = {'Clock methods':'CLOCK_METHODS.md', 'Clock validation':'CLOCK_VALIDATION.md',
             'Clock results & reproduction':'CLOCK_PERFORMANCE.md', 'Stability methodology':'METHODOLOGY.md',
             'ODMR methods':'ODMR_METHODS.md', 'Optical methods':'OPTICAL_METHODS.md',
             'Optical validation':'OPTICAL_VALIDATION.md', 'Provenance & references':'PROVENANCE_AND_REFERENCES.md',
             'NV geometry':'NV_VISUALIZATION.md', 'Interactive ODMR':'NV_ODMR_DEMONSTRATION.md'}


def catalog():
    try:
        return ReferenceStore().catalog(), None
    except (OSError, sqlite3.Error, ValueError) as exc:
        return sources(), str(exc)


def parameter_table(area, config):
    """Existing parameter reporters only; no Hamiltonian, spectrum or clock solve."""
    if area == 'Stability & compensation':
        return provenance(config)
    if area == 'ODMR spectroscopy':
        from .odmr import ODMRConfig, odmr_parameter_provenance
        saved=st.session_state.get('odmr_result')
        return odmr_parameter_provenance(ODMRConfig(**saved[0][0]) if saved else ODMRConfig())
    if area == 'Optical readout':
        from .optical_parameters import OpticalExperiment, parameter_records
        from .optical_parameters import OpticalConfig, OpticalRates, Detector
        saved=st.session_state.get('optical_result')
        values=dict(saved[0][0]) if saved else {}
        for key,cls in (('optical',OpticalConfig),('rates',OpticalRates),('detector',Detector)):
            if key in values:values[key]=cls(**values[key])
        return pd.DataFrame(parameter_records(OpticalExperiment(**values)))
    from .clock_parameters import ClockExperiment
    from .clock_results import experiment
    from .clock_reporting import clock_parameters
    saved=st.session_state.get('clock_result')
    return clock_parameters(experiment(saved[0][0]) if saved else ClockExperiment())


def render_paper_bucket(config=None, *, standalone=True):
    if standalone:st.title('Paper Bucket')
    st.caption('Trace equations, constants and assumptions to the recorded source and implementation.')
    c=config or Config(**st.session_state.get('legacy_config',{}))
    reference_store=None
    paper_bucket,reference_error=catalog()
    if reference_error:st.error('Persistent references unavailable: '+reference_error)
    else:reference_store=ReferenceStore()
    query=st.text_input('Search papers, equations, parameters, or implementation',key='legacy_search_papers_equations_parameters_or_implementation')
    papers_tab,maps_tab,parameters_tab,attribution_tab=st.tabs(['References','Equation maps','Parameter sources','MATLAB attribution'])
    with papers_tab:
        with st.expander('Add a paper'):
            st.caption('Saved references remain unverified and unmapped until independently reviewed. A DOI alone is not verification.')
            with st.form('add_paper'):
                title=st.text_input('Title',key='legacy_title')
                authors=st.text_input('Authors',key='legacy_authors')
                year=st.number_input('Publication year',min_value=1800,max_value=2100,value=2026,step=1,key='legacy_publication_year')
                journal=st.text_input('Journal or publication',key='legacy_journal_or_publication')
                doi=st.text_input('DOI (optional)',key='legacy_doi_optional')
                url=st.text_input('Paper URL',key='legacy_paper_url')
                note=st.text_area('Note (optional)',key='legacy_note_optional')
                submitted=st.form_submit_button('Add paper',type='primary')
            if submitted:
                try:
                    if reference_store is None:raise ValueError('Persistent storage is unavailable. Reference was not saved.')
                    reference_store.add(dict(title=title,authors=authors,year=year,journal=journal,doi=doi,url=url,note=note))
                    paper_bucket=reference_store.catalog()
                    st.session_state.pop('export',None)
                    st.success(f'Added "{title.strip()}". Saved as unverified.')
                except (ValueError,OSError,sqlite3.Error) as exc:st.error(str(exc))
        paper_count=sum(s['id']!='MODEL' and s.get('record_type')!='implementation_archive' for s in paper_bucket)
        st.caption(f'{paper_count} papers/research references · {len(paper_bucket)} total records. Verification labels retain their original scope.')
        a,b=st.columns(2)
        a.download_button('Download Paper Bucket JSON',catalog_bytes(paper_bucket),'sources.json','application/json',disabled=reference_error is not None)
        b.download_button('Download Paper Bucket BibTeX',bibtex_bytes(paper_bucket),'references.bib','application/x-bibtex',disabled=reference_error is not None)
        for source in sorted(paper_bucket,key=lambda s:(s['year'],s['title'].lower())):
            if query and query.lower() not in json.dumps(source).lower():continue
            with st.expander(f"[{source['id']}] {source['title']} ({source['year']})"):
                st.write(source['authors']+' · '+source['journal'])
                st.write('Verification: '+verification_label(source))
                st.write('Evidence: '+source['evidence'])
                st.write('Location: '+source['locator'])
                st.code(source['implementation'],language=None)
                st.write(source['note'])
                if source.get('doi'):st.link_button('DOI: '+source['doi'],'https://doi.org/'+source['doi'])
                if source.get('url','').startswith(('https://','http://')):st.link_button('Source link',source['url'])
    with maps_tab:
        area=st.selectbox('Equation map',list(MAPS),key='research_equation_map')
        st.caption('MODEL and project-derived entries identify assumptions or numerical methods, not published validation. Unmapped user references supply no equation attribution.')
        st.markdown((ROOT/'references'/MAPS[area]).read_text(encoding='utf-8'))
    with parameters_tab:
        area=st.selectbox('Parameter model',list(MAPS)[:4],key='research_parameter_model')
        st.caption('Values use the last completed model configuration where available, otherwise declared defaults. Stability uses its last configured inputs. This table does not run a model.')
        try:
            data=parameter_table(area,c)
            lookup={row['id']:row for row in paper_bucket}
            data['Reference status']=data.source.map(lambda key:verification_label(lookup[key]) if key in lookup else 'Unmapped source ID; no attribution inferred')
            if query:data=data[data.astype(str).apply(lambda col:col.str.contains(query,case=False,regex=False)).any(axis=1)]
            st.dataframe(data,hide_index=True,width='stretch')
        except (KeyError,TypeError,ValueError):st.warning('Saved parameter configuration is incompatible. Open its research workspace to configure a new run.')
        with st.expander('Published measurement limits'):
            st.dataframe(benchmarks(),hide_index=True,width='stretch')
            st.caption('Reported upper bounds, not imported raw data or predictions for this simulator.')
    with attribution_tab:
        st.markdown((ROOT/'legacy/matlab/README.md').read_text(encoding='utf-8'))
        st.download_button('Download original MATLAB transcript',(ROOT/'legacy/matlab/intern_odmr_as_supplied.m.txt').read_bytes(),'intern_odmr_as_supplied.m.txt','text/plain',key='paper_matlab_transcript')
    return paper_bucket,hashlib.sha256(catalog_bytes(paper_bucket)).hexdigest(),reference_error


def render_prepared_exports():
    papers,error=catalog()
    if error:st.error('Reference catalog unavailable: '+error)
    fingerprint=source_fingerprint()
    json_digest=hashlib.sha256(json.dumps(papers,sort_keys=True).encode()).hexdigest()
    catalog_digest=hashlib.sha256(catalog_bytes(papers)).hexdigest()
    found=False
    # Respect the original source/configuration/catalog bindings; never recalculate.
    for label,key,result_key in (('Photon clock','clock_export','clock_result'),('ODMR','odmr_export','odmr_result'),('Optical readout','optical_export','optical_result')):
        saved=st.session_state.get(key)
        result=st.session_state.get(result_key)
        if not saved:continue
        found=True
        try:
            if error or not result or saved[:2]!=(result[0],json_digest) or result[0][-1]!=fingerprint:
                raise ValueError('Source, configuration or reference catalog changed. Prepare a fresh export in its workspace.')
            if result_key=='clock_result':
                from .clock_results import validate_saved
                validate_saved(result)
            else:validate(result[1]['context'])
            payload=zip_files(saved[2]) if isinstance(saved[2],dict) else saved[2]
            st.download_button('Download '+label+' research bundle',payload,key+'_SIMULATION.zip','application/zip',key='hub_'+key)
        except (ValueError,KeyError,TypeError) as exc:st.warning(label+': '+str(exc))
    saved=st.session_state.get('export')
    if saved:
        found=True
        if not error and saved[0][1:]==(fingerprint,catalog_digest):
            try:
                verify_files(saved[1])
                st.download_button('Download stability research bundle',zip_files(saved[1]),'DiamondClock_stability_SIMULATION.zip','application/zip',key='hub_legacy_export')
            except ValueError as exc:st.warning(str(exc))
        else:st.warning('Stability export is stale. Prepare a fresh export in Stability & compensation.')
    if not found:st.caption('No prepared session bundles. Run an experiment and prepare its bundle in Clock Performance or Research Tools.')
    a,b=st.columns(2)
    a.download_button('Reference catalog · JSON',catalog_bytes(papers),'sources.json','application/json',disabled=error is not None)
    b.download_button('Reference catalog · BibTeX',bibtex_bytes(papers),'references.bib','application/x-bibtex',disabled=error is not None)


def render_exports():
    st.title('Exports & Documentation')
    session,archived,documentation=st.tabs(['Session bundles','Saved scientific outputs','Methods & limitations'])
    with session:render_prepared_exports()
    with archived:
        from .clock_presentation import CASES, read_archive, render_vector_downloads
        name=st.selectbox('Archived experiment',list(CASES),key='research_export_case')
        path=ROOT/'outputs/clock_phase4_20261024'/CASES[name]/'complete_research_bundle.zip'
        if path.is_file():
            data=path.read_bytes()
            try:
                _,_,metadata,files=read_archive(data)
                st.caption('Original verified SIMULATION outputs; source snapshot and configuration are retained in the bundle.')
                st.download_button('Download original complete research bundle',data,CASES[name]+'_HISTORICAL_SIMULATION.zip','application/zip',key='hub_archive_zip')
                render_vector_downloads(files)
                st.download_button('Original configuration',files['config.json'],'config.json','application/json',key='hub_archive_config')
                st.download_button('Original provenance metadata',files['metadata.json'],'metadata.json','application/json',key='hub_archive_metadata')
            except (ValueError,KeyError,OSError) as exc:st.error('Archive verification failed: '+str(exc))
        else:st.caption('Historical outputs require the Git checkout; they are not included in wheels.')
    with documentation:
        name=st.selectbox('Scientific documentation',list(DOCUMENTS),key='research_document')
        path=ROOT/'docs'/DOCUMENTS[name]
        st.download_button('Download document',path.read_bytes(),path.name,'text/markdown')
        st.markdown(path.read_text(encoding='utf-8'))
