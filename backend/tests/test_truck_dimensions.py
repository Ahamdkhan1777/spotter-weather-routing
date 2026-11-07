"""Dimension parsing and outgoing routing parameters; no live provider requests."""
from datetime import datetime, timezone
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from config.truck import DIMENSION_FIELDS, load_truck_dimensions
from services.routing import calculate_routes
from tests.test_api import route_fixture


class TruckDimensionTests(SimpleTestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('Live HTTP is disabled in dimension tests.')))

    def test_unset_dimensions_are_omitted(self):
        self.assertEqual(load_truck_dimensions({}), {})

    def test_blank_and_whitespace_dimensions_are_omitted(self):
        for blank in ['', ' ', '\t\n']:
            with self.subTest(blank=repr(blank)):
                self.assertEqual(load_truck_dimensions({name: blank for name, _ in DIMENSION_FIELDS}), {})

    def test_each_dimension_maps_to_its_own_parameter(self):
        for name, parameter in DIMENSION_FIELDS:
            with self.subTest(variable=name):
                self.assertEqual(load_truck_dimensions({name: '2.55'}), {parameter: 2.55})

    def test_all_dimensions_preserve_values_in_metres(self):
        # Synthetic test values only; never written to the real vehicle configuration.
        self.assertEqual(load_truck_dimensions({'TRUCK_HEIGHT_M': '4.05', 'TRUCK_WIDTH_M': '2.55', 'TRUCK_LENGTH_M': '16.5'}),
                         {'vehicleHeight': 4.05, 'vehicleWidth': 2.55, 'vehicleLength': 16.5})

    def test_surrounding_whitespace_is_accepted(self):
        self.assertEqual(load_truck_dimensions({'TRUCK_HEIGHT_M': ' 4.05\t'}), {'vehicleHeight': 4.05})

    def test_zero_and_negative_dimensions_are_rejected(self):
        self.check_invalid_values(['0', '0.0', '-0', '-0.01', '-5'])

    def test_nonfinite_dimensions_are_rejected(self):
        self.check_invalid_values(['NaN', 'nan', 'inf', '-inf', 'Infinity', '1e309'])

    def test_nonnumeric_dimensions_are_rejected(self):
        self.check_invalid_values(['abc', '4 metres', '2,55', 'true'])

    def test_parsing_does_not_modify_the_supplied_environment(self):
        values = {'TRUCK_HEIGHT_M': ' 4.05 ', 'TRUCK_WIDTH_M': '', 'UNRELATED': 'leave unchanged'}
        original = values.copy()
        load_truck_dimensions(values)
        self.assertEqual(values, original)

    def check_invalid_values(self, values):
        for name, _ in DIMENSION_FIELDS:
            for value in values:
                with self.subTest(variable=name, value=value):
                    with self.assertRaises(ImproperlyConfigured) as error:
                        load_truck_dimensions({name: value})
                    self.assertIn(name, str(error.exception))
                    self.assertIn('positive number in metres, or blank', str(error.exception))

    def assert_routing_dimensions(self, configured):
        with override_settings(TOMTOM_API_KEY='dimension-test-only', TRUCK_EMPTY_WEIGHT_LB=18000, TRUCK_DIMENSIONS=configured), \
                patch('services.routing.get_json', return_value=route_fixture()) as provider:
            routes, _ = calculate_routes({'coordinates': [-96, 32]}, {'coordinates': [-95.5, 32.4]},
                                         datetime(2026, 11, 7, 12, tzinfo=timezone.utc), 30000)
            self.assertEqual(len(routes), 1)
            provider.assert_called_once()
            parameters = provider.call_args.args[1]
            self.assertEqual({key: parameters[key] for _, key in DIMENSION_FIELDS if key in parameters}, configured)
            self.assertEqual(parameters['travelMode'], 'truck')
            self.assertEqual(parameters['vehicleWeight'], 21773)

    def test_blank_dimensions_are_not_sent_to_routing_provider(self):
        self.assert_routing_dimensions(load_truck_dimensions({'TRUCK_HEIGHT_M': '', 'TRUCK_WIDTH_M': '', 'TRUCK_LENGTH_M': ''}))

    def test_partial_dimensions_only_send_configured_measurements(self):
        self.assert_routing_dimensions(load_truck_dimensions({'TRUCK_HEIGHT_M': '4.05', 'TRUCK_WIDTH_M': '', 'TRUCK_LENGTH_M': ''}))

    def test_all_dimensions_are_sent_to_routing_provider(self):
        self.assert_routing_dimensions(load_truck_dimensions({'TRUCK_HEIGHT_M': '4.05', 'TRUCK_WIDTH_M': '2.55', 'TRUCK_LENGTH_M': '16.5'}))
