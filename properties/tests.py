from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase

from .models import Property
from .utils import get_all_properties, get_redis_cache_metrics


class PropertyCachingTests(TestCase):
    """These tests use the real Redis cache from settings."""

    def setUp(self):
        cache.clear()
        Property.objects.create(title='Sea view flat', description='Two bedrooms', price=Decimal('120.00'), location='Mbabane')

    def tearDown(self):
        cache.clear()

    def test_queryset_is_cached(self):
        self.assertIsNone(cache.get('all_properties'))
        self.assertEqual(len(get_all_properties()), 1)
        self.assertEqual(len(cache.get('all_properties')), 1)
        with self.assertNumQueries(0):
            get_all_properties()

    def test_signals_invalidate_cache(self):
        get_all_properties()
        prop = Property.objects.create(title='Cabin', description='Quiet', price=Decimal('80.00'), location='Piggs Peak')
        self.assertIsNone(cache.get('all_properties'))
        self.assertEqual(len(get_all_properties()), 2)
        prop.delete()
        self.assertIsNone(cache.get('all_properties'))

    def test_list_view(self):
        response = self.client.get('/properties/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['properties'][0]['price'], '120.00')
        # The whole response is cached for 15 minutes
        self.assertIn('max-age=900', response['Cache-Control'])

    def test_metrics(self):
        cache.get('missing-key')
        metrics = get_redis_cache_metrics()
        self.assertNotIn('error', metrics)
        self.assertGreaterEqual(metrics['keyspace_misses'], 1)
        self.assertTrue(0 <= metrics['hit_ratio'] <= 100)
