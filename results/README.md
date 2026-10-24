# Saved experiments

- `scaling/`: original eight-workload experiment, five trials at each of six sizes.
- `operations/`: combined prebuilt-tree experiment, currently four trials per size.
- `operations_2trials/` and `operations_trials3_4/`: source runs retained for provenance.
- `scaling/plots/`: four PNG report figures generated from scaling and operations.

Each size contains raw measurements, summary statistics, and run metadata. Keep
these files together. Metadata records the original machine paths for provenance;
those paths are not required to plot the saved results on another computer.

Old exploratory results and smoke tests are retained locally under
`.local_archive/` and excluded from Git. Large generated key files are also
excluded; use the dataset generator or the separately hosted dataset.

Do not describe the operation results as five trials until a fifth real trial has
been incorporated and the summaries and figures regenerated. Source measurements
must not be duplicated to increase the trial count.
