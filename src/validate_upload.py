#!/usr/bin/env python3

import argparse
import sys
from glob import glob
from pathlib import Path
import inspect

from ingest_validation_tools.error_report import ErrorReport
from ingest_validation_tools.upload import Upload
from ingest_validation_tools import argparse_types
from ingest_validation_tools.argparse_types import ShowUsageException
from ingest_validation_tools.check_factory import cache_path

directory_schemas = sorted({
    p.stem for p in
    (Path(__file__).parent / 'ingest_validation_tools' /
     'directory-schemas').glob('*.yaml')
})


VALID_STATUS = 0
BUG_STATUS = 1
ERROR_STATUS = 2
INVALID_STATUS = 3


def make_parser():
    parser = argparse.ArgumentParser(
        description='''
Validate a HuBMAP upload, both the metadata TSVs, and the datasets,
either local or remote, or a combination of the two.''',
        epilog=f'''
Typical usage:
  --tsv_paths: Used to validate Sample metadata TSVs. (Because it does
  not check references, should not be used to validate Dataset metadata TSVs.)

  --local_directory: Used by lab before upload, and on Globus after upload.

  --local_directory + --dataset_ignore_globs + --upload_ignore_globs:
  After the initial validation on Globus, the metadata TSVs are broken up,
  and one-line TSVs are put in each dataset directory. This structure needs
  extra parameters.

Exit status codes:
  {VALID_STATUS}: Validation passed
  {BUG_STATUS}: Unexpected bug
  {ERROR_STATUS}: User error
  {INVALID_STATUS}: Validation failed
''',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # What should be validated?

    mutex_group = parser.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument(
        '--local_directory', type=argparse_types.dir_path,
        metavar='PATH',
        help='Local directory to validate')
    mutex_group.add_argument(
        '--tsv_paths', nargs='+',
        metavar='PATH',
        help='Paths of metadata.tsv files.')

    # Should validation be loosened?

    parser.add_argument(
        '--optional_fields', nargs='+',
        metavar='FIELD', default=[],
        help='The listed fields will be treated as optional. '
        '(But if they are supplied in the TSV, they will be validated.)'
    )
    parser.add_argument(
        '--offline', action='store_true',
        help='Skip checks that require network access.'
    )
    parser.add_argument(
        '--clear_cache', action='store_true',
        help='Clear cache of network check responses.'
    )

    default_ignore = '.*'
    parser.add_argument(
        '--dataset_ignore_globs', nargs='+',
        metavar='GLOB',
        default=[default_ignore],
        help=f'Matching files in each dataset directory will be ignored. Default: {default_ignore}'
    )
    parser.add_argument(
        '--upload_ignore_globs', nargs='+',
        metavar='GLOB',
        help='Matching sub-directories in the upload will be ignored.'
    )

    default_encoding = 'ascii'
    parser.add_argument(
        '--encoding', default=default_encoding,
        help=f'Character-encoding to use for parsing TSVs. Default: {default_encoding}. '
        'Work-in-progress: https://github.com/hubmapconsortium/ingest-validation-tools/issues/494'
    )

    # Are there plugin validations?

    parser.add_argument('--plugin_directory', action='store',
                        help='Directory of plugin tests.')

    # How should output be formatted?

    error_report_methods = [
        name for (name, type) in inspect.getmembers(ErrorReport)
        if name.startswith('as_')
    ]
    parser.add_argument('--output', choices=error_report_methods,
                        default='as_text_list')

    parser.add_argument('--add_notes', action='store_true',
                        help='Append a context note to error reports.')

    return parser


# We want the error handling inside the __name__ == '__main__' section
# to be able to show the usage string if it catches a ShowUsageException.
# Defining this at the top level makes that possible.
parser = make_parser()


def parse_args():
    args = parser.parse_args()
    if not (args.tsv_paths or args.local_directory):
        raise ShowUsageException(
            'Either local file or local directory is required')

    return args


def main():
    args = parse_args()

    if args.clear_cache:
        for path in glob(f'{cache_path}*'):
            Path(path).unlink()

    upload_args = {
        'add_notes': args.add_notes,
        'encoding': args.encoding,
        'offline': args.offline,
        'optional_fields': args.optional_fields
    }

    if args.local_directory:
        upload_args['directory_path'] = Path(args.local_directory)

    if args.tsv_paths:
        upload_args['tsv_paths'] = args.tsv_paths

    if args.dataset_ignore_globs:
        upload_args['dataset_ignore_globs'] = \
            args.dataset_ignore_globs
    if args.upload_ignore_globs:
        upload_args['upload_ignore_globs'] = \
            args.upload_ignore_globs
    if args.plugin_directory:
        upload_args['plugin_directory'] = \
            args.plugin_directory

    upload = Upload(**upload_args)
    errors = upload.get_errors()
    report = ErrorReport(errors)
    print(getattr(report, args.output)())
    return INVALID_STATUS if errors else VALID_STATUS


if __name__ == "__main__":
    try:
        exit_status = main()
    except ShowUsageException as e:
        print(parser.format_usage(), file=sys.stderr)
        print(e, file=sys.stderr)
        exit_status = ERROR_STATUS
    sys.exit(exit_status)