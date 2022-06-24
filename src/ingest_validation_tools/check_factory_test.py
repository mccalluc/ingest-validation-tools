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
    tasks = report['tasks']
    assert len(tasks) == 1
    return tasks[0]['errors']


def test_expected_error():
    schema = {
        'fields': [
            {'name': 'this_name_will_not_match'}
        ]
    }
    errors = validate(schema)
    assert errors[0]['description'] == \
        'One of the data source header does not match the field name defined in the schema.'
