from .check_factory import make_checks

def test_fake():
    make_checks(schema={
        'fields': [
            {
                'name': 'a_field',
                'custom_constraints': []
            }
        ]
    })
