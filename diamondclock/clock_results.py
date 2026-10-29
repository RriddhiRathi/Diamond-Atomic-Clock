"""Read-only adapters for completed Phase 4 results; no solver calls.

Allan comparisons use positive finite values at exactly matched tau within one
analysis window. `locked` is the engine's feedback-enabled branch, not a lock claim.
"""
from dataclasses import asdict
import hashlib
import json

import numpy as np
import pandas as pd

from .clock_parameters import ClockExperiment, ControllerConfig
from .optical_parameters import OpticalConfig, OpticalRates, Detector
from .oscillator import OscillatorConfig
from .clock_reporting import table_hashes
from .run_provenance import source_fingerprint, validate


WINDOWS = {'Full record': 'allan', 'Predeclared fixed window': 'allan_fixed_window'}


def experiment(values):
    """Reconstruct the existing nested configuration without changing defaults."""
    values = dict(values)
    for name, cls in (('optical', OpticalConfig), ('rates', OpticalRates),
                      ('detector', Detector), ('controller', ControllerConfig),
                      ('oscillator', OscillatorConfig)):
        values[name] = cls(**values[name])
    config = ClockExperiment(**values)
    config.validate()
    return config


def validate_saved(saved):
    """Reject stale, incompatible or modified session results, retaining the object."""
    try:
        (values, fingerprint), result = saved
        if fingerprint != source_fingerprint():
            raise ValueError('Source changed. Run the clock again in Research Mode.')
        config = experiment(values)
        context = result['context']
        validate(context)
        if context['config'] != asdict(config):
            raise ValueError('Clock result configuration differs from its captured run.')
        if context['validation_protocol'] != result['validation_protocol']:
            raise ValueError('Clock validation protocol changed.')
        if table_hashes(result['tables']) != result['table_sha256']:
            raise ValueError('Clock tables changed after calculation.')
        digest = hashlib.sha256(json.dumps(result['summary'], sort_keys=True).encode()).hexdigest()
        if digest != result['summary_sha256']:
            raise ValueError('Clock summary changed after calculation.')
        summary = result['summary']
        if summary['data_kind'] != 'SIMULATION' or summary['experimental_validation'] is not False:
            raise ValueError('Only identified simulation results are supported.')
        for name in ('clock_output', 'clock_phase_boundaries', 'photon_observations',
                     'acquisition', 'feedback', 'allan', 'allan_fixed_window', 'actuation'):
            if not isinstance(result['tables'][name], pd.DataFrame):
                raise ValueError('Incompatible clock result tables.')
        if not 0 <= summary['observed_lock_fraction'] <= 1:
            raise ValueError('Invalid observed lock fraction.')
        return config, result
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise ValueError('Incompatible saved clock result. Run the clock again in Research Mode.') from exc


def valid_allan(table):
    """Drop invalid/ambiguous samples; do not interpolate, extrapolate or fit."""
    columns = ['method', 'tau_s', 'adev']
    if table is None or not set(columns).issubset(table.columns):
        return pd.DataFrame(columns=columns)
    data = table.copy()
    for col in ('tau_s', 'adev'):
        data[col] = pd.to_numeric(data[col], errors='coerce')
    good = (np.isfinite(data.tau_s) & (data.tau_s > 0) &
            np.isfinite(data.adev) & (data.adev > 0) & data.method.isin(('locked', 'unlocked')))
    if 'overlapping_pairs' in data:
        pairs = pd.to_numeric(data.overlapping_pairs, errors='coerce')
        good &= np.isfinite(pairs) & (pairs > 0)
    data = data.loc[good]
    return data.loc[~data.duplicated(['method', 'tau_s'], keep=False)].sort_values('tau_s')


def matched_allan(table):
    data = valid_allan(table)
    if data.empty:
        return pd.DataFrame({name:pd.Series(dtype=float) for name in
                             ('tau_s','free_adev','feedback_adev','ratio')})
    free = data[data.method == 'unlocked'][['tau_s', 'adev']].rename(columns={'adev': 'free_adev'})
    corrected = data[data.method == 'locked'][['tau_s', 'adev']].rename(columns={'adev': 'feedback_adev'})
    paired = free.merge(corrected, on='tau_s', how='inner', validate='one_to_one').sort_values('tau_s')
    with np.errstate(over='ignore', under='ignore', divide='ignore', invalid='ignore'):
        paired['ratio'] = paired.feedback_adev / paired.free_adev
    return paired[np.isfinite(paired.ratio) & (paired.ratio > 0)].reset_index(drop=True)


def ratio_outcome(ratio):
    if not np.isfinite(ratio) or ratio <= 0:
        return 'unavailable'
    # Report floating-point equality; do not turn tiny numerical noise into a claim.
    if np.isclose(ratio, 1., rtol=1e-10, atol=0.):
        return 'equal within numerical tolerance'
    return 'improved' if ratio < 1 else 'worsened'


def interpret(result, window='allan'):
    """Evidence across ALL available matched tau, not a selected best-lock window."""
    tables = result['tables']
    fb = tables['feedback']
    flags = fb['locked'].dropna() if 'locked' in fb else pd.Series(dtype=bool)
    known = len(flags) and flags.isin([True, False]).all()
    ever = bool(flags.any()) if known else None
    final = bool(flags.iloc[-1]) if known else None
    lock = ('Lock not observed' if ever is False else
            'Lock observed; final cycle locked' if final else
            'Lock observed; lost by final cycle' if ever else 'Lock status unavailable')
    paired = matched_allan(tables.get(window))
    outcomes = [ratio_outcome(r) for r in paired.ratio]
    lower, higher = outcomes.count('improved'), outcomes.count('worsened')
    if not len(paired):
        stability = 'insufficient comparable Allan data'
    elif lower and higher:
        stability = 'stability depends on averaging time'
    elif higher:
        stability = 'feedback worsens stability at the compared averaging times'
    elif lower:
        stability = 'feedback improves stability at the compared averaging times'
    else:
        stability = 'equal Allan deviation within numerical tolerance'
    window_label = ('full record, including acquisition and failures' if window == 'allan'
                    else 'predeclared fixed window; not selected by lock quality')
    text = f'{lock}. {stability.capitalize()} ({window_label}). '
    if len(paired):
        text += (f'Across {len(paired)} matched τ points from {paired.tau_s.min():g} to '
                 f'{paired.tau_s.max():g} s: {lower} lower, {higher} higher, '
                 f'{len(paired)-lower-higher} equal within numerical tolerance. ')
    else:
        text += 'No valid positive pair at the same averaging time supports a stability ratio. '
    if result['summary'].get('timed_out'):
        text += 'The simulation reached its time limit; the requested record was not completed. '
    text += 'Observed lock is a count-based detector decision. Lower Allan deviation does not establish absolute accuracy.'
    return dict(lock=lock, ever_locked=ever, final_locked=final, stability=stability,
                text=text, paired=paired)


def overview_metrics(values, result):
    """Values remain engine outputs; the ratio is the sole derived performance metric."""
    summary = result['summary']
    paired = matched_allan(result['tables'].get('allan'))
    selected = paired.iloc[-1].to_dict() if len(paired) else None
    return dict(states=values['optical']['states'], nominal_Hz=summary.get('nominal_Hz'),
                lock_fraction=summary.get('observed_lock_fraction'), record_s=summary.get('record_s'),
                final_time_errors_s=summary.get('final_time_errors_s', {}), comparison=selected,
                interpretation=interpret(result))
