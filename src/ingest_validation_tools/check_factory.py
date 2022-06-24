import re
from string import Template
from pathlib import Path
from sys import stderr
import json
from typing import List, Callable, Dict, Any, Iterator

import frictionless
import requests


cache_path = Path(__file__).parent / 'url-status-cache.json'

ErrorIterator = Iterator[frictionless.errors.CellError]
Row = Dict[str, Any]
Check = Callable[[Row], ErrorIterator]


def make_checks(schema) -> List[Check]:
    factory = _CheckFactory(schema)
    return [
        factory.make_url_check(),
        factory.make_sequence_limit_check(),
        factory.make_units_check(),
        factory.make_forbid_na_check(),
        # TODO:
        # factory.make_at_least_one_check(),
    ]


class _CheckFactory():
    def __init__(self, schema):
        self.schema = schema
        self._prev_value_run_length = {}

    def _get_constrained_fields(self, constraint: str) -> Dict[str, List]:
        c_c = 'custom_constraints'
        return {
            f['name']: f[c_c][constraint] for f in self.schema['fields']
            if c_c in f and constraint in f[c_c]
        }

    def _check_url_status_cache(self, url: str) -> str:
        if not cache_path.exists():
            cache_path.write_text('{}')
        url_status_cache = json.loads(cache_path.read_text())
        if url not in url_status_cache:
            print(f'Fetching un-cached url: {url}', file=stderr)
            try:
                response = requests.get(url)
                url_status_cache[url] = response.status_code
            except Exception as e:
                url_status_cache[url] = str(e)
            cache_path.write_text(json.dumps(
                url_status_cache,
                sort_keys=True,
                indent=2
            ))
        return url_status_cache[url]

    def make_url_check(self, template=Template(
            'URL returned $status: "$url"')) -> Check:
        url_constrained_fields = self._get_constrained_fields('url')

        def url_check(row):
            for k, v in row.items():
                if v is None:
                    continue
                if k in url_constrained_fields:
                    prefix = url_constrained_fields[k]['prefix']
                    url = f'{prefix}{v}'
                    status = self._check_url_status_cache(url)
                    if status != 200:
                        note = template.substitute(status=status, url=url)
                        yield frictionless.errors.CellError.from_row(row, note=note, field_name=k)
        return url_check

    def make_sequence_limit_check(self, template=Template(
            'there is a run of $run_length sequential items: Limit is $limit. '
            'If correct, reorder rows.')) -> Check:
        sequence_limit_fields = self._get_constrained_fields('sequence_limit')

        def sequence_limit_check(row):
            prefix_number_re = r'(?P<prefix>.*?)(?P<number>\d+)$'
            for k, v in row.items():
                # If the schema declares the field as datetime,
                # "v" will be a python object, and regexes will error.
                v = str(v)

                if k not in sequence_limit_fields or not v:
                    continue

                match = re.search(prefix_number_re, v)
                if not match:
                    if k in self._prev_value_run_length:
                        del self._prev_value_run_length[k]
                    continue

                if k not in self._prev_value_run_length:
                    self._prev_value_run_length[k] = (v, 1)
                    continue

                prev_value, run_length = self._prev_value_run_length[k]
                prev_match = re.search(prefix_number_re, prev_value)
                if (
                    match.group('prefix') != prev_match.group('prefix') or
                    int(match.group('number')) != int(prev_match.group('number')) + 1
                ):
                    self._prev_value_run_length[k] = (v, 1)
                    continue

                run_length += 1
                self._prev_value_run_length[k] = (v, run_length)

                limit = sequence_limit_fields[k]
                assert limit > 1, 'The lowest allowed limit is 2'
                if run_length >= limit:
                    note = template.substitute(run_length=run_length, limit=limit)
                    yield frictionless.errors.CellError.from_row(row, note=note, field_name=k)

        return sequence_limit_check

    def make_units_check(self, template=Template(
            'Required when $units_for is filled')) -> Check:
        units_constrained_fields = self._get_constrained_fields('units_for')

        def units_check(row):
            for k, v in row.items():
                if k in units_constrained_fields:
                    units_for = units_constrained_fields[k]
                    if (row[units_for] or row[units_for] == 0) and not row[k]:
                        note = template.substitute(units_for=units_for)
                        yield frictionless.errors.CellError.from_row(row, note=note, field_name=k)
        return units_check

    def make_forbid_na_check(self, template=Template(
            '"N/A" fields should just be left empty')) -> Check:
        forbid_na_constrained_fields = self._get_constrained_fields('forbid_na')

        def forbid_na_check(row):
            for k, v in row.items():
                if (
                    k in forbid_na_constrained_fields
                    and isinstance(v, str)
                    and v.upper() in ['NA', 'N/A']
                ):
                    note = template.substitute()
                    yield frictionless.errors.CellError.from_row(row, note=note, field_name=k)
        return forbid_na_check

    # def make_at_least_one_check(self, template=Template(
    #         'At least one row in this column must be filled')) -> Check:
    #     # # constrained_fields = set(self._get_constrained_fields('at_least_one'))
    #     # # constrained_fields_with_data = set()

    #     # def at_least_one_check(row):
    #     #     return
    #     #     for k, v in row.items():
    #     #         continue
    #     #         if (k in constrained_fields and v):
    #     #             # TODO: above causes "NoneType' object is not iterable"
    #     #             constrained_fields_with_data.add(k)
    #     #     # TODO:
    #     #     # if last row, and constrained_fields != constrained_fields_with_data
    #     #     #    error!
    #     #     # note = template.substitute()
    #     #     # yield frictionless.errors.CellError.from_row(row, note=note, field_name=k)
    #     # return at_least_one_check

    #     constrained_fields = set(self._get_constrained_fields('at_least_one'))
    #     constrained_fields_with_data = set()
    #     raise Exception('???', self)

    #     def at_least_one_check(row):
    #         for k, v in row.items():
    #             if (
    #                 k in constrained_fields
    #                 and v
    #             ):
    #                 # import pdb; pdb.set_trace()
    #                 constrained_fields_with_data.add(k)
    #                 note = template.substitute()
    #                 yield frictionless.errors.CellError.from_row(row, note=note, field_name=k)
    #     return at_least_one_check
