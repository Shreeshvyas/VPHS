# d:\vphs\seed_data.py
import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_erp.settings')
django.setup()

from django.contrib.auth import get_user_model
from academics.models import AcademicSession, ClassLevel, Section, ClassSection, Subject
from fees.models import FeeType, ClassFeeStructure, StudentFeeStructure
from students.models import Student, StudentEnrollment
from staff.models import Staff, SalaryStructure, SalaryPayment

User = get_user_model()

def seed():
    print("Seeding initial database data...")

    # 1. Create Users
    admin_user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@vyaspublicschool.edu",
            "first_name": "Super",
            "last_name": "Admin",
            "role": "SUPER_ADMIN",
            "is_staff": True,
            "is_superuser": True
        }
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save()
        print("-> Created Super Admin account: admin / admin123")
    else:
        print("-> Super Admin 'admin' already exists.")

    accountant_user, created = User.objects.get_or_create(
        username="accountant",
        defaults={
            "email": "finance@vyaspublicschool.edu",
            "first_name": "Vijay",
            "last_name": "Sharma",
            "role": "ACCOUNTANT",
            "is_staff": True
        }
    )
    if created:
        accountant_user.set_password("accountant123")
        accountant_user.save()
        print("-> Created Accountant account: accountant / accountant123")

    principal_user, created = User.objects.get_or_create(
        username="principal",
        defaults={
            "email": "principal@vyaspublicschool.edu",
            "first_name": "Anjali",
            "last_name": "Mehta",
            "role": "PRINCIPAL",
            "is_staff": True
        }
    )
    if created:
        principal_user.set_password("principal123")
        principal_user.save()
        print("-> Created Principal account: principal / principal123")

    # 2. Create Active Academic Session
    session, created = AcademicSession.objects.get_or_create(
        name="2026-2027",
        defaults={
            "start_date": datetime.date(2026, 4, 1),
            "end_date": datetime.date(2027, 3, 31),
            "is_active": True
        }
    )
    if created:
        print("-> Created Academic Session: 2026-2027 (Active)")

    # 3. Create Class Levels
    class_names = ["Nursery", "LKG", "UKG", "Class 1", "Class 5", "Class 10", "Class 12"]
    class_objs = {}
    for name in class_names:
        cls, _ = ClassLevel.objects.get_or_create(name=name)
        class_objs[name] = cls
    print(f"-> Created {len(class_names)} Class Levels.")

    # 4. Create Sections
    sec_a, _ = Section.objects.get_or_create(name="A")
    sec_b, _ = Section.objects.get_or_create(name="B")
    print("-> Created Sections: A, B")

    # 5. Map Class-Sections
    cs_objs = {}
    for name, cls in class_objs.items():
        cs_a, _ = ClassSection.objects.get_or_create(class_level=cls, section=sec_a)
        cs_objs[f"{name}-A"] = cs_a
        cs_b, _ = ClassSection.objects.get_or_create(class_level=cls, section=sec_b)
        cs_objs[f"{name}-B"] = cs_b
    print("-> Mapped Classes and Sections.")

    # 6. Create Fee Types
    fee_types = ["Tuition Fee", "Computer Fee", "Transport Fee", "Admission Fee"]
    ft_objs = {}
    for name in fee_types:
        ft, _ = FeeType.objects.get_or_create(name=name)
        ft_objs[name] = ft
    print("-> Created Fee Types.")

    # 7. Create Class Fee Structures for all class levels
    for cls_name, cls in class_objs.items():
        # Tuition Fee: Nursery/LKG/UKG: $1000, Class 1-5: $1500, Class 10-12: $2500
        if cls_name in ["Nursery", "LKG", "UKG"]:
            tuition = 1000.00
            computer = 100.00
            transport = 300.00
        elif cls_name in ["Class 1", "Class 5"]:
            tuition = 1500.00
            computer = 200.00
            transport = 500.00
        else: # Class 10, Class 12
            tuition = 2500.00
            computer = 300.00
            transport = 600.00

        ClassFeeStructure.objects.get_or_create(
            academic_session=session,
            class_level=cls,
            fee_type=ft_objs["Tuition Fee"],
            defaults={"amount": tuition, "payment_frequency": "MONTHLY", "due_day_of_month": 10}
        )
        ClassFeeStructure.objects.get_or_create(
            academic_session=session,
            class_level=cls,
            fee_type=ft_objs["Computer Fee"],
            defaults={"amount": computer, "payment_frequency": "MONTHLY", "due_day_of_month": 10}
        )
        ClassFeeStructure.objects.get_or_create(
            academic_session=session,
            class_level=cls,
            fee_type=ft_objs["Transport Fee"],
            defaults={"amount": transport, "payment_frequency": "MONTHLY", "due_day_of_month": 10}
        )
    print("-> Configured Class Fee Structures for all classes.")

    # 8. Create 150 Students with mixed payment statuses
    from decimal import Decimal
    from fees.models import FeeCollection, FeeCollectionItem
    from finance.models import CashBookEntry

    indian_first_names = [
        "Aarav", "Ishaan", "Vihaan", "Aditya", "Arjun", "Sai", "Krishna", "Ananya", "Diya", "Aaradhya",
        "Avani", "Isha", "Riya", "Yash", "Rohan", "Dev", "Aryan", "Kabir", "Meera", "Nehal",
        "Amit", "Vijay", "Rohit", "Sneha", "Neha", "Ritu", "Divya", "Nisha", "Pooja", "Sanjay",
        "Ramesh", "Suresh", "Ganesh", "Kartik", "Karan", "Kunal", "Harish", "Mohit", "Pankaj", "Sunil",
        "Kiran", "Geeta", "Babita", "Kavita", "Lata", "Asha", "Sita", "Radha", "Rukmini", "Meena"
    ]
    indian_last_names = [
        "Sharma", "Verma", "Gupta", "Patel", "Mehta", "Kumar", "Singh", "Joshi", "Iyer", "Nair",
        "Sen", "Bose", "Das", "Roy", "Ray", "Mishra", "Prasad", "Reddy", "Rao", "Chaudhary",
        "Trivedi", "Pathak", "Pandey", "Dwivedi", "Bhatt", "Kulkarni", "Deshmukh", "Patil", "Desai", "Shah"
    ]

    print("Seeding 150 students...")
    cs_keys = list(cs_objs.keys()) # All Class-Section mappings

    for i in range(1, 151):
        first = indian_first_names[(i - 1) % len(indian_first_names)]
        last = indian_last_names[(i * 3) % len(indian_last_names)]
        adm_no = f"SA-2026-{1000 + i}"
        
        student = Student.objects.create(
            admission_number=adm_no,
            first_name=first,
            last_name=last,
            father_name=f"{first} Father",
            mother_name=f"{first} Mother",
            guardian_name=f"{first} Father",
            guardian_relation="Father",
            guardian_mobile=f"987654{1000 + i:04d}",
            address=f"Flat {100+i}, Heights Apartments",
            city="Metropolis",
            state="Delhi",
            date_of_birth=datetime.date(2015, 1, 1) + datetime.timedelta(days=(i * 15) % 1500),
            gender='M' if i % 2 == 0 else 'F',
            admission_date=datetime.date(2026, 4, 1),
            category='GEN' if i % 3 == 0 else 'OBC'
        )

        cs_mapping = cs_objs[cs_keys[(i - 1) % len(cs_keys)]]
        enrollment = StudentEnrollment.objects.create(
            student=student,
            academic_session=session,
            class_section=cs_mapping,
            roll_number=(i % 30) + 1
        )

        # Create Dues based on Class Fee Structures
        cfss = ClassFeeStructure.objects.filter(academic_session=session, class_level=cs_mapping.class_level)
        due_items = []
        for cfs in cfss:
            net_amt = cfs.amount
            # Seed Tuition Fee, Computer Fee, Transport Fee
            due = StudentFeeStructure.objects.create(
                student_enrollment=enrollment,
                fee_type=cfs.fee_type,
                original_amount=cfs.amount,
                net_amount=net_amt,
                due_date=datetime.date(2026, 6, 10),
                status="UNPAID"
            )
            due_items.append(due)

        total_due = sum(d.net_amount for d in due_items)

        # Mixed Payment Statuses:
        # i in 1..60: fully paid
        # i in 61..100: partially paid (pays half of dues)
        # i in 101..150: unpaid (keep unpaid)
        if i <= 60:
            receipt_no = f"RC-202606-{100000 + i}"
            collection = FeeCollection.objects.create(
                student_enrollment=enrollment,
                receipt_number=receipt_no,
                amount_paid=total_due,
                fine_applied=Decimal('0.00'),
                discount_applied=Decimal('0.00'),
                payment_date=datetime.date(2026, 6, 1) + datetime.timedelta(days=i % 7),
                payment_mode='CASH' if i % 3 == 0 else 'UPI',
                transaction_id=f"TXN{12345678+i}" if i % 3 != 0 else "",
                remarks="Initial seeded payment",
                accountant=accountant_user
            )

            for due in due_items:
                due.paid_amount = due.net_amount
                due.status = 'PAID'
                due.save()

                FeeCollectionItem.objects.create(
                    fee_collection=collection,
                    student_fee_structure=due,
                    amount_allocated=due.net_amount
                )

            # Cashbook debit entry
            pmode = 'BANK' if collection.payment_mode != 'CASH' else 'CASH'
            CashBookEntry.create_entry(
                entry_date=collection.payment_date,
                entry_type='DEBIT',
                category='FEE_COLLECTION',
                amount=collection.amount_paid,
                payment_mode=pmode,
                reference_id=receipt_no,
                description=f"Fee collection from {student.full_name} ({student.admission_number})",
                user=accountant_user
            )
        elif i <= 100:
            # Partially paid: pay off Tuition Fee only, leave others unpaid
            tuition_due = next(d for d in due_items if d.fee_type == ft_objs["Tuition Fee"])
            receipt_no = f"RC-202606-{100000 + i}"
            
            collection = FeeCollection.objects.create(
                student_enrollment=enrollment,
                receipt_number=receipt_no,
                amount_paid=tuition_due.net_amount,
                fine_applied=Decimal('0.00'),
                discount_applied=Decimal('0.00'),
                payment_date=datetime.date(2026, 6, 1) + datetime.timedelta(days=i % 7),
                payment_mode='UPI',
                transaction_id=f"TXN{12345678+i}",
                remarks="Seeded partial payment (Tuition only)",
                accountant=accountant_user
            )

            tuition_due.paid_amount = tuition_due.net_amount
            tuition_due.status = 'PAID'
            tuition_due.save()

            FeeCollectionItem.objects.create(
                fee_collection=collection,
                student_fee_structure=tuition_due,
                amount_allocated=tuition_due.net_amount
            )

            # Cashbook debit entry
            CashBookEntry.create_entry(
                entry_date=collection.payment_date,
                entry_type='DEBIT',
                category='FEE_COLLECTION',
                amount=collection.amount_paid,
                payment_mode='BANK',
                reference_id=receipt_no,
                description=f"Fee collection (Tuition) from {student.full_name} ({student.admission_number})",
                user=accountant_user
            )

    print(f"-> Created 150 students with realistic dues and payments.")

    # 9. Create 20 Teachers / Staff Profiles and payroll history
    print("Seeding 20 staff/teachers...")
    staff_names = [
        ("Rajesh", "Kumar"), ("Sunita", "Sharma"), ("Amit", "Patel"), ("Priya", "Verma"),
        ("Neha", "Singh"), ("Deepak", "Gupta"), ("Sanjay", "Joshi"), ("Manoj", "Mehta"),
        ("Anil", "Trivedi"), ("Jyoti", "Mishra"), ("Pooja", "Chaudhary"), ("Vikram", "Reddy"),
        ("Shalini", "Sen"), ("Ramesh", "Pathak"), ("Gauri", "Kulkarni"), ("Alok", "Patil"),
        ("Swati", "Desai"), ("Manish", "Verma"), ("Kavita", "Bhatt"), ("Ritu", "Pandey")
    ]

    for j in range(1, 21):
        first, last = staff_names[j - 1]
        emp_id = f"EMP-{1000 + j}"
        
        # Designations & Departments mapping
        if j <= 16:
            desig = 'TEACHER'
            dept = 'ACADEMICS'
            base_sal = Decimal(f"{3000.00 + (j * 100)}")
        elif j <= 18:
            desig = 'CLERK'
            dept = 'ADMINISTRATION'
            base_sal = Decimal('2200.00')
        elif j == 19:
            desig = 'ACCOUNTANT'
            dept = 'ACCOUNTS'
            base_sal = Decimal('3500.00')
        else:
            desig = 'DRIVER'
            dept = 'SUPPORT'
            base_sal = Decimal('1800.00')

        staff = Staff.objects.create(
            employee_id=emp_id,
            first_name=first,
            last_name=last,
            department=dept,
            designation=desig,
            mobile=f"987655{1000+j:04d}",
            address=f"Street {j}, Teacher Colony",
            joining_date=datetime.date(2025, 1, 1),
            status="ACTIVE",
            base_salary=base_sal,
            bank_name="State Bank of India",
            bank_account_number=f"9876543210{j}",
            ifsc_code="SBIN0001234"
        )

        # Create SalaryStructure
        allowance = Decimal('200.00') if desig == 'TEACHER' else Decimal('100.00')
        pf = Decimal('150.00')
        tax = Decimal('50.00')
        
        SalaryStructure.objects.create(
            staff=staff,
            basic_salary=base_sal,
            allowance_default=allowance,
            pf_deduction_default=pf,
            tax_deduction_default=tax
        )

        # Create a PAID Salary Payment for April 2026
        net_pay = base_sal + allowance - pf - tax
        payslip_no = f"SL-202604-{emp_id}"
        
        salary_paid = SalaryPayment.objects.create(
            staff=staff,
            academic_session=session,
            month=4,
            year=2026,
            base_salary=base_sal,
            bonus=allowance,
            deductions=pf + tax,
            net_salary=net_pay,
            payslip_number=payslip_no,
            payment_status="PAID",
            payment_date=datetime.date(2026, 5, 1),
            payment_mode="BANK_TRANSFER",
            transaction_id=f"TXN9812{7000+j}",
            processed_by=admin_user
        )

        # Create Cashbook Entry (CREDIT) for salary payout
        CashBookEntry.create_entry(
            entry_date=datetime.date(2026, 5, 1),
            entry_type='CREDIT',
            category='SALARY',
            amount=net_pay,
            payment_mode='BANK',
            reference_id=payslip_no,
            description=f"Salary paid to {staff.full_name} ({emp_id}) for April 2026",
            user=admin_user
        )

        # Create a PENDING Salary Payment for May 2026
        SalaryPayment.objects.create(
            staff=staff,
            academic_session=session,
            month=5,
            year=2026,
            base_salary=base_sal,
            bonus=allowance,
            deductions=pf + tax,
            net_salary=net_pay,
            payslip_number=f"SL-202605-{emp_id}",
            payment_status="PENDING"
        )

    print("-> Created 20 staff/teachers with salary structures, paid April slips, and pending May slips.")
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed()

