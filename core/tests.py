import threading
from datetime import date
from decimal import Decimal
from django.test import TransactionTestCase, TestCase
from django.db import IntegrityError, connections
from core.models import Customer, Supplier, DocumentSequenceCounter
from core.services.sequence import next_number


class SequenceConcurrencyTests(TransactionTestCase):
    def test_concurrent_sequence_generation_uniqueness(self):
        """
        Verify that 50 concurrent threads requesting sequence numbers
        generate 50 unique document numbers without collision or gaps.
        """
        today = date(2026, 11, 15)
        generated_numbers = []
        errors = []
        threads = []

        def worker():
            try:
                num = next_number('SJ', today)
                generated_numbers.append(num)
            except Exception as e:
                errors.append(e)
            finally:
                for conn in connections.all(initialized_only=True):
                    conn.close()

        for _ in range(50):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors encountered: {errors}")
        self.assertEqual(len(generated_numbers), 50)
        self.assertEqual(len(set(generated_numbers)), 50, "Generated duplicate document sequence numbers!")

        counter = DocumentSequenceCounter.objects.get(doc_type='SJ', period_key='202611')
        self.assertEqual(counter.last_number, 50)


class CustomerSupplierConstraintTests(TestCase):
    def test_customer_credit_limit_non_negative_constraint(self):
        with self.assertRaises(IntegrityError):
            Customer.objects.create(
                code='CUST-FAIL',
                name='Negative Credit Customer',
                credit_limit=Decimal('-1000.00')
            )
