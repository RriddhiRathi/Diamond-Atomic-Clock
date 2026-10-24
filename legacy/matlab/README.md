# Original intern implementation: attribution archive

`intern_odmr_as_supplied.m.txt` preserves the user-supplied MATLAB transcript,
including malformed syntax, missing functions, HTML/Markdown artifacts, inconsistent
names, and disabled nuclear terms. Whitespace was normalized when transcribing the
chat; this is **not** a byte-identical original .m file or a runnable MATLAB program.
No original disk file, author name, date, or license was supplied. Authorship of
that implementation belongs to the original intern, not to this Python integration.
The user explicitly requested retaining it for attribution and comparison.

The functional Python adaptation lives in `diamondclock/odmr.py`. It corrects the
Hamiltonian, transitions, coordinates, units, and plotting integration. Detailed
changes and scientific limits are recorded in `docs/ODMR_METHODS.md`. The original
transcript cannot be a numerical gold standard because it does not execute.
Analytic limits and overlap with the existing tested Python engine are the
numerical validation references. No MATLAB execution equivalence is claimed.
