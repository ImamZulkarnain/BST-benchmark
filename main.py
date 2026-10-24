"""Single command-line entry point for data, benchmarks, plots, and tests."""

import argparse
from pathlib import Path


def main(argv=None):
    """Parse a command and run the selected project task."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command_parser = commands.add_parser('generate', help='Generate')
    command_parser.add_argument('--output', type=Path, default=Path('data/generated/sample'))
    command_parser.add_argument('--count', type=int, default=1000)
    command_parser.add_argument('--missing-count', type=int, default=1000)
    command_parser.add_argument('--seed', type=int, default=520)
    command_parser.add_argument('--min-length', type=int, default=10)
    command_parser.add_argument('--max-length', type=int, default=24)

    command_parser = commands.add_parser('workloads', help='Workloads')
    command_parser.add_argument('--dataset', type=Path, default=Path('data/generated/sample'))
    command_parser.add_argument('--output', type=Path, default=Path('results/sample'))
    command_parser.add_argument('--trials', type=int, default=5)
    command_parser.add_argument('--sizes', nargs='+', type=int,
                        help='Prefix sizes to benchmark from the same dataset')
    command_parser.add_argument('--no-progress', action='store_true', help='Use plain phase messages instead of a progress bar')
    command_parser.add_argument('--seed', type=int, default=520)
    command_parser.add_argument('--queries', type=int, default=None)
    command_parser.add_argument('--skip-validation', action='store_true', help='Skip full structural/key validation; still check result counts and sizes')

    command_parser = commands.add_parser('operations', help='Operations')
    command_parser.add_argument('--dataset', type=Path, default=Path('data/generated/sample'))
    command_parser.add_argument('--output', type=Path, default=Path('results/operations'))
    command_parser.add_argument('--sizes', nargs='+', type=int)
    command_parser.add_argument('--trials', type=int, default=5)
    command_parser.add_argument('--seed', type=int, default=520)
    command_parser.add_argument('--skip-validation', action='store_true')
    command_parser.add_argument('--no-progress', action='store_true')

    command_parser = commands.add_parser('plot', help='Plot')
    command_parser.add_argument('--results', nargs='+', type=Path, help='Result folders or parent folders containing multiple sizes')
    command_parser.add_argument('--operations', nargs='+', type=Path, help='Operation-run folders or their parent directory')
    command_parser.add_argument('--output', type=Path, default=Path('results/plots'))
    command_parser.add_argument('--size', type=int, help='Size for bar charts; defaults to the largest available')

    commands.add_parser('test', help='Run the unit tests using small datasets')
    args = parser.parse_args(argv)
    try:
        if args.command == 'generate':
            from data.generate import generate_dataset
            generate_dataset(args.output, args.count, args.missing_count, args.seed,
                             args.min_length, args.max_length)
            print(f'Dataset saved to {args.output}')
        elif args.command == 'workloads':
            from benchmarks.workload_runner import run_benchmarks
            run_benchmarks(args.dataset, args.output, args.trials, args.seed,
                           args.queries, not args.skip_validation,
                           sizes=args.sizes, progress=not args.no_progress)
            print(f'Results saved to {args.output}')
        elif args.command == 'operations':
            from benchmarks.operation_runner import run_operations
            run_operations(args.dataset, args.output, args.trials, args.seed,
                           args.sizes, not args.skip_validation, not args.no_progress)
            print(f'Results saved to {args.output}')
        elif args.command == 'plot':
            from benchmarks.plot import create_plots, discover_results
            directories = discover_results(args.results or [Path('results/scaling')])
            operations = discover_results(args.operations) if args.operations else None
            for path in create_plots(directories, args.output, args.size, operations):
                print(f'Saved {path}')
        elif args.command == 'test':
            import unittest
            root = Path(__file__).resolve().parent
            suite = unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            return 0 if result.wasSuccessful() else 1
    except ImportError as error:
        parser.error(f'{error}. Install dependencies with: python -m pip install -r requirements.txt')
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
