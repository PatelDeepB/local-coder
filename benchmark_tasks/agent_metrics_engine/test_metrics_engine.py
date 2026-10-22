from __future__ import annotations
import unittest
from aggregator import Aggregator
from alert_engine import AlertEngine, AlertRule
from models import MetricPoint


class TestMetricsEngine(unittest.TestCase):
    def test_aggregation_functions(self):
        aggregator = Aggregator()
        aggregator.add_data_point(MetricPoint(1, 10))
        aggregator.add_data_point(MetricPoint(2, 20))
        aggregator.add_data_point(MetricPoint(3, 30))

        self.assertEqual(aggregator.count(), 3)
        self.assertEqual(aggregator.sum(), 60)
        self.assertEqual(aggregator.avg(), 20.0)
        self.assertEqual(aggregator.min(), 10)
        self.assertEqual(aggregator.max(), 30)
        self.assertEqual(aggregator.p95(), 28)

    def test_tag_filtering(self):
        aggregator = Aggregator(filter_tags={"env": "prod"})
        aggregator.add_data_point(MetricPoint(1, 10, tags={"env": "prod"}))
        aggregator.add_data_point(MetricPoint(2, 50, tags={"env": "dev"}))
        aggregator.add_data_point(MetricPoint(3, 20, tags={"env": "prod"}))

        self.assertEqual(aggregator.count(), 2)
        self.assertEqual(aggregator.sum(), 30)
        self.assertEqual(aggregator.avg(), 15.0)

    def test_rule_evaluation(self):
        rule = AlertRule("LOW", 15)
        aggregator = Aggregator()
        aggregator.add_data_point(MetricPoint(1, 10))
        aggregator.add_data_point(MetricPoint(2, 20))
        aggregator.add_data_point(MetricPoint(3, 30))

        self.assertFalse(rule.evaluate(aggregator.min()))
        self.assertTrue(rule.evaluate(aggregator.max()))


if __name__ == '__main__':
    unittest.main()
