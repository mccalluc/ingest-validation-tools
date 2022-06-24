from pathlib import Path

import frictionless

from .check_factory import make_checks


def validate(schema):
    checks = make_checks(schema=schema)
    report = frictionless.validate(
        source=(Path(__file__).parent / 'check_factory_test_fixture.csv').absolute(),
        schema=schema,
        checks=checks
    )
    assert not report['errors']
    return report


def test_expected_error():
    schema = {
        'fields': [
            {'name': 'this_name_will_not_match'}
        ]
    }
    report = validate(schema)
    tasks = report['tasks']
    assert len(tasks) == 1
    assert tasks[0]['errors'][0]['description'] == \
        'One of the data source header does not match the field name defined in the schema.'
