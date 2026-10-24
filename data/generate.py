"""Generate disjoint, unique alphanumeric key files for tree benchmarks."""

import json
import random
import string
from collections import Counter
from pathlib import Path

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
GENERATOR_VERSION = 1


def generate_dataset(output, count=1000, missing_count=1000, seed=520,
                     min_length=10, max_length=24):
    """Write stored and absent keys plus a manifest; return the manifest.

    Lengths are sampled uniformly (inclusive), characters uniformly from
    ALPHABET. Reject duplicates across both files. A fixed seed and options
    reproduce the files. Output must be a new directory to avoid overwrites.
    The uniqueness set uses O(count + missing_count) memory; files stream to
    disk. This is synthetic benchmark data, not security-sensitive data.
    """
    if count < 1 or missing_count < 0:
        raise ValueError('count must be positive and missing_count nonnegative')
    if not 10 <= min_length <= max_length <= 24:
        raise ValueError('lengths must satisfy 10 <= min_length <= max_length <= 24')
    capacity = sum(len(ALPHABET) ** length for length in range(min_length, max_length + 1))
    if count + missing_count > capacity:
        raise ValueError('Requested more unique keys than the available key space')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)

    # A fixed seed reproduces the same sequence of random choices.
    rng = random.Random(seed)

    # Share one set across both files so insertion and missing keys never overlap.
    seen = set()
    files = {}
    for filename, total in [('insert_keys.txt', count), ('missing_keys.txt', missing_count)]:
        lengths = Counter()
        with (output / filename).open('wb') as stream:
            for _ in range(total):
                # Retry duplicates instead of writing the same key twice.
                while True:
                    length = rng.randint(min_length, max_length)
                    key = ''.join(rng.choice(ALPHABET) for _ in range(length))
                    if key not in seen:
                        seen.add(key)
                        break
                record = (key + '\n').encode('ascii')
                stream.write(record)
                lengths[length] += 1
        files[filename] = {
            'count': total,
            'length_counts': {str(k): lengths[k] for k in range(min_length, max_length + 1)},
        }

    # Save the settings and counts used to describe and check this dataset.
    manifest = {
        'generator_version': GENERATOR_VERSION,
        'seed': seed,
        'alphabet': ALPHABET,
        'min_length': min_length,
        'max_length': max_length,
        'length_distribution': 'uniform inclusive; duplicate candidates rejected',
        'format': 'ASCII, one key per line, LF line endings',
        'ordering': 'case-sensitive Python lexicographic order',
        'uniqueness': 'unique within and disjoint across both files',
        'files': files,
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest
