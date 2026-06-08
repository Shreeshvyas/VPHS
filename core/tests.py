from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from core.models import SoftDeleteModel
from users.models import User
from users.decorators import role_required
from academics.models import AcademicSession, ClassLevel, Section, ClassSection
from students.models import Student, StudentEnrollment
from fees.models import FeeType, StudentFeeStructure, FeeCollection
from finance.models import CashBookEntry

# Simple model for testing soft deletes
class DummySoftDeleteModel(SoftDeleteModel):
    name = models.CharField(max_length=50) if False else None # dynamic helper
    # We will just test with User model which inherits SoftDeleteModel!

class SoftDeleteTestCase(TestCase):
    def test_soft_delete_lifecycle(self):
        # Create a user (which inherits SoftDeleteModel)
        user = User.objects.create_user(username="testuser", email="test@test.com", password="password123")
        
        self.assertFalse(user.is_deleted)
        self.assertIsNone(user.deleted_at)
        
        # Soft delete
        user.delete()
        
        # Reload from db
        # Standard manager should exclude it
        self.assertFalse(User.objects.filter(username="testuser").exists())
        
        # all_objects manager should see it
        deleted_user = User.all_objects.get(username="testuser")
        self.assertTrue(deleted_user.is_deleted)
        self.assertIsNotNone(deleted_user.deleted_at)
        
        # Restore
        deleted_user.restore()
        self.assertFalse(deleted_user.is_deleted)
        self.assertIsNone(deleted_user.deleted_at)
        self.assertTrue(User.objects.filter(username="testuser").exists())


class PermissionTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.accountant = User.objects.create_user(username="acct", password="password", role="ACCOUNTANT")
        self.teacher = User.objects.create_user(username="teach", password="password", role="TEACHER")

    def test_role_decorator_authorization(self):
        @role_required('ACCOUNTANT')
        def test_view(request):
            return "SUCCESS"
            
        # Try as accountant
        request = self.factory.get('/dummy-url/')
        request.user = self.accountant
        response = test_view(request)
        self.assertEqual(response, "SUCCESS")
        
        # Try as teacher (should raise PermissionDenied)
        request.user = self.teacher
        with self.assertRaises(PermissionDenied):
            test_view(request)


class CashBookIntegrityTestCase(TestCase):
    def setUp(self):
        self.accountant = User.objects.create_user(username="acc_user", password="password", role="ACCOUNTANT")
        self.session = AcademicSession.objects.create(name="2026-2027", start_date="2026-04-01", end_date="2027-03-31", is_active=True)
        self.cls = ClassLevel.objects.create(name="Class 1")
        self.sec = Section.objects.create(name="A")
        self.cs = ClassSection.objects.create(class_level=self.cls, section=self.sec)
        
        self.student = Student.objects.create(
            admission_number="ADM-9999", first_name="John", last_name="Doe",
            father_name="F", mother_name="M", guardian_name="G", guardian_relation="Father",
            guardian_mobile="12345", address="Add", city="C", state="S",
            date_of_birth="2018-01-01", admission_date="2026-06-08", category="GEN"
        )
        self.enrollment = StudentEnrollment.objects.create(student=self.student, academic_session=self.session, class_section=self.cs, roll_number=1)
        self.fee_type = FeeType.objects.create(name="Tuition Fee")
        self.due = StudentFeeStructure.objects.create(
            student_enrollment=self.enrollment, fee_type=self.fee_type,
            original_amount=1000.00, net_amount=1000.00, due_date="2026-06-10"
        )

    def test_payment_cashbook_debit(self):
        # Generate collection and verify cashbook log
        initial_entries = CashBookEntry.objects.count()
        self.assertEqual(initial_entries, 0)
        
        # Simulate payment mode CASH
        collection = FeeCollection.objects.create(
            student_enrollment=self.enrollment,
            receipt_number="RC-2026-999999",
            amount_paid=1000.00,
            payment_mode="CASH",
            payment_date=timezone.now().date(),
            accountant=self.accountant
        )
        
        # Manually invoke CashBookEntry create (mimics collect_fee view workflow)
        CashBookEntry.create_entry(
            entry_date=collection.payment_date,
            entry_type='DEBIT',
            category='FEE_COLLECTION',
            amount=collection.amount_paid,
            payment_mode='CASH',
            reference_id=collection.receipt_number,
            description="Fee Payment Test",
            user=self.accountant
        )
        
        self.assertEqual(CashBookEntry.objects.count(), 1)
        entry = CashBookEntry.objects.first()
        self.assertEqual(entry.entry_type, 'DEBIT')
        self.assertEqual(entry.amount, 1000.00)
        self.assertEqual(entry.running_cash_balance, 1000.00)
        self.assertEqual(entry.running_bank_balance, 0.00)
