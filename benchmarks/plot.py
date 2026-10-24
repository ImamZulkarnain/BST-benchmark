"""Create report figures from saved tree benchmark measurements."""

import csv
import json
import math
import statistics
from pathlib import Path

TREES = ('AVLTree', 'RedBlackTree', 'SplayTree')
LABELS = {'AVLTree': 'AVL', 'RedBlackTree': 'Red-black', 'SplayTree': 'Splay'}
COLORS = {'AVLTree': '#0072B2', 'RedBlackTree': '#D55E00', 'SplayTree': '#009E73'}
INSERT = ('insert_random', 'insert_sorted', 'insert_reverse')
SEARCH = ('search_uniform', 'search_missing', 'search_sequential', 'search_hotspot')
WORKLOADS = INSERT + SEARCH + ('delete_random',)
OPERATIONS = ('insert_existing', 'delete_existing', 'search_existing')
NAMES = {
    'insert_random': 'Random insertion', 'insert_sorted': 'Ascending insertion',
    'insert_reverse': 'Descending insertion', 'search_uniform': 'Uniform hits',
    'search_missing': 'Missing keys', 'search_sequential': 'Sequential hits',
    'search_hotspot': 'Hotspot hits', 'delete_random': 'Random deletion',
}


def load_results(directories, workloads=WORKLOADS):
    """Read raw trial CSVs and return grouped measurements and run metadata.

    Compute medians and ranges from raw trials, using the same median rule as
    summary.csv. Require complete, comparable workloads. Do not pool separate
    runs at the same size, which could hide different experiment settings.
    """
    groups, metadata = {}, []
    owners = {}
    for directory in directories:
        directory = Path(directory)
        meta = json.loads((directory / 'metadata.json').read_text(encoding='utf-8'))
        if meta.get('status') != 'complete':
            raise ValueError(f'Run is not complete: {directory}')
        metadata.append(meta)
        with (directory / 'raw.csv').open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise ValueError(f'No measurements in {directory}')
        seen = set()
        for row in rows:
            tree, workload = row['tree'], row['workload']
            if tree not in TREES or workload not in workloads:
                raise ValueError(f'Unknown tree or workload in {directory}')
            for name in ('key_count', 'operation_count', 'trial', 'rotations', 'height_before', 'height_after'):
                row[name] = int(row[name])
            row['seconds'] = float(row['seconds'])
            if (row['key_count'] < 2 or row['operation_count'] < 1 or row['trial'] < 1
                    or row['seconds'] <= 0 or not math.isfinite(row['seconds']) or row['rotations'] < 0):
                raise ValueError(f'Invalid measurement in {directory}')
            identity = (row['key_count'], tree, workload, row['trial'])
            if identity in seen:
                raise ValueError(f'Duplicate trial in {directory}: {identity}')
            seen.add(identity)
            size = row['key_count']
            if size in owners and owners[size] != directory:
                raise ValueError(f'Multiple runs for size {size}; select just one result directory per size')
            owners[size] = directory
            groups.setdefault((size, tree, workload), []).append(row)

    # Every size must have all trees and workloads with matching trial counts.
    for size in owners:
        trial_sets = []
        for workload in workloads:
            counts = set()
            for tree in TREES:
                trials = groups.get((size, tree, workload))
                if not trials:
                    raise ValueError(f'Missing {tree}/{workload} for size {size}')
                trial_sets.append({r['trial'] for r in trials})
                counts.update(r['operation_count'] for r in trials)
                if any(r['height_after'] < 0 for r in trials) and workload != 'delete_random':
                    raise ValueError('Nonempty trees must have nonnegative heights')
            if len(counts) != 1:
                raise ValueError(f'Operation counts differ for {workload} at size {size}')
            if workload in INSERT + ('delete_random',) and counts != {size}:
                raise ValueError('Insertion and deletion must process every stored key')
            if workload in OPERATIONS:
                expected = max(10000, size // 100) if workload == 'search_existing' else max(1, size // 100)
                if counts != {expected}:
                    raise ValueError('Operation batch count does not match the experiment rule')
        if any(trials != trial_sets[0] for trials in trial_sets):
            raise ValueError(f'Trials differ between workloads at size {size}')
    return groups, metadata


def statistics_for(groups, size, tree, workload, metric):
    """Return the median, minimum, and maximum for a plotted measurement."""
    values = []
    for row in groups[(size, tree, workload)]:
        if metric == 'microseconds':
            value = row['seconds'] * 1e6 / row['operation_count']
        elif metric == 'rotations_per_operation':
            value = row['rotations'] / row['operation_count']
        else:
            value = row[metric]
        values.append(value)
    return statistics.median(values), min(values), max(values)


def style_axis(ax, ylabel):
    """Apply consistent axis styling without hiding zero measurements."""
    ax.set_ylabel(ylabel)
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#dddddd', linewidth=0.7)
    ax.spines[['top', 'right']].set_visible(False)


def grouped_bars(ax, groups, size, workloads, metric, ylabel, names=None,
                 trees=TREES, show_values=False):
    """Compare tree medians and trial ranges in grouped bars."""
    width = 0.24
    for offset, tree in enumerate(trees):
        stats = [statistics_for(groups, size, tree, workload, metric) for workload in workloads]
        medians = [s[0] for s in stats]
        positions = [index + (offset - (len(trees) - 1) / 2) * width for index in range(len(workloads))]
        errors = [[s[0] - s[1] for s in stats], [s[2] - s[0] for s in stats]]
        ax.bar(positions, medians, width, yerr=errors, capsize=3,
               color=COLORS[tree], label=LABELS[tree], error_kw={'linewidth': 1})

        # Mark zero values explicitly so a missing bar is not mistaken for missing data.
        for x, value, stat in zip(positions, medians, stats):
            if show_values:
                ax.annotate(f'{value:.3f}', (x, stat[2]), xytext=(0, 6),
                            textcoords='offset points', ha='center', fontsize=9)
            elif value == 0:
                ax.annotate('0', (x, 0), xytext=(0, 4), textcoords='offset points',
                            ha='center', fontsize=8, color=COLORS[tree])
    ax.set_xticks(range(len(workloads)), names or [NAMES[w] for w in workloads])
    style_axis(ax, ylabel)
    ax.set_ylim(bottom=0)
    ax.margins(y=0.15)


def save_figure(fig, name, title, output, plt):
    """Save each figure as a high-resolution PNG."""
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    # Collect legends across panels, keeping one entry for each tree.
    legend = {}
    for ax in fig.axes:
        handles, labels = ax.get_legend_handles_labels()
        legend.update(zip(labels, handles))
    labels, handles = list(legend), list(legend.values())
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.925),
               ncol=3, frameon=False)
    fig.tight_layout(rect=(0.02, 0.02, 0.99, 0.86))
    fig.savefig(output / f'{name}.png', dpi=220, facecolor='white')
    plt.close(fig)


def plot_operations(groups, metadata, output, plt):
    """Compare average operation time with initial tree size on a log x-axis."""
    sizes = sorted({key[0] for key in groups})
    fig, axes = plt.subplots(1, 3, figsize=(13, 6.4))
    titles = ('Insertion', 'Deletion', 'Successful search (uniform random)')
    for ax, workload, title in zip(axes, OPERATIONS, titles):
        for tree in TREES:
            stats = [statistics_for(groups, size, tree, workload, 'microseconds') for size in sizes]
            ax.errorbar(sizes, [s[0] for s in stats],
                        yerr=[[s[0] - s[1] for s in stats], [s[2] - s[0] for s in stats]],
                        color=COLORS[tree], label=LABELS[tree], marker='o', capsize=3,
                        linestyle='-' if len(sizes) > 1 else 'none')
        ax.set_xscale('log')
        ax.set_xlabel('Initial tree size (log scale)')
        ax.set_title(title)
        style_axis(ax, 'Average time per operation (microseconds)')
        ax.set_ylim(bottom=0)
    warnings = []
    if len(sizes) < 3:
        warnings.append('Fewer than three sizes: preliminary measurements only.')
    environments = {(m.get('python'), m.get('platform'), m.get('processor')) for m in metadata}
    if len(environments) > 1:
        warnings.append('Operation runs used different environments; compare cautiously.')
    save_figure(fig, 'operation_times', 'Operation time on prebuilt trees', output, plt)
    return warnings


def create_plots(directories, output, size=None, operation_directories=None):
    """Create three workload figures and, when supplied, the operation figure."""
    groups, metadata = load_results(directories)
    sizes = sorted({key[0] for key in groups})
    size = max(sizes) if size is None else size
    if size not in sizes:
        raise ValueError(f'No measurements for size {size}; available sizes: {sizes}')

    operation_data = load_results(operation_directories, OPERATIONS) if operation_directories else None

    # Use a file-only backend so running this script does not open GUI windows.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 12})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    warnings = []

    # Remove only the retired figure outputs in this selected output directory.
    for filename in ('runtime_growth.png', 'runtime_growth.pdf'):
        try:
            (output / filename).unlink(missing_ok=True)
        except PermissionError:
            warnings.append(f'Could not remove {filename}; close any viewer and remove it manually.')
    if operation_data:
        warnings.extend(plot_operations(*operation_data, output, plt))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8))
    names = ['Random', 'Ascending', 'Descending']
    grouped_bars(axes[0], groups, size, INSERT, 'seconds', 'Insertion time (seconds)', names)
    grouped_bars(axes[1], groups, size, INSERT, 'height_after', 'Final height (edges, log scale)', names)
    axes[0].set_title('Construction time')
    axes[1].set_title('Resulting tree height')
    axes[1].set_yscale('log')
    axes[1].set_ylim(bottom=0.8)
    save_figure(fig, 'insertion_order', 'Effect of insertion order', output, plt)

    fig, ax = plt.subplots(figsize=(12, 5.8))
    grouped_bars(ax, groups, size, SEARCH, 'microseconds', 'Time per search (microseconds)')
    save_figure(fig, 'search_patterns', 'Effect of search patterns', output, plt)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2),
                             gridspec_kw={'width_ratios': [1, 1.65]})
    workloads = ('insert_random',) + SEARCH + ('delete_random',)
    names = ['Random\ninsertion', 'Uniform\nhits', 'Missing\nkeys',
             'Sequential\nhits', 'Hotspot\nhits', 'Random\ndeletion']

    # Separate scales make the small AVL/red-black rotation rates readable.
    grouped_bars(axes[0], groups, size, ('insert_random', 'delete_random'),
                 'rotations_per_operation', 'Rotations per operation',
                 ['Random insertion', 'Random deletion'],
                 trees=('AVLTree', 'RedBlackTree'), show_values=True)
    axes[0].set_title('AVL and red-black: updates')
    axes[0].set_ylim(top=max(1, axes[0].get_ylim()[1]))
    grouped_bars(axes[1], groups, size, workloads, 'rotations_per_operation',
                 'Rotations per operation', names, trees=('SplayTree',), show_values=True)
    axes[1].set_title('Splay: all access patterns')
    save_figure(fig, 'rotations_per_operation',
                'Tree rotations per operation - different vertical scales', output, plt)
    for warning in warnings:
        print('Note:', warning)
    names = ['insertion_order', 'search_patterns', 'rotations_per_operation']
    if operation_data:
        names.append('operation_times')
    return [output / f'{name}.png' for name in names]


def discover_results(paths):
    """Find result folders inside selected runs or a scaling-results directory."""
    directories = set()
    for path in paths:
        path = Path(path)
        if not path.is_dir():
            raise ValueError(f'Result directory does not exist: {path}')
        if (path / 'raw.csv').is_file():
            directories.add(path.resolve())
        else:
            directories.update(p.parent.resolve() for p in path.rglob('raw.csv'))
    if not directories:
        raise ValueError('No raw.csv result files found in the selected folders')
    return sorted(directories)
