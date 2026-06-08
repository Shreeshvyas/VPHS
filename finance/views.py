import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils.timezone import now

from users.decorators import accountant_only, staff_only, principal_only, admin_only
from users.middleware import log_activity
from .models import Expense, Income, CashBookEntry, log_financial_change
from .forms import ExpenseForm, IncomeForm

# Expense views
@login_required
@staff_only
def expense_list(request):
    query = request.GET.get('q', '')
    cat_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    expenses = Expense.objects.filter(is_deleted=False)
    
    if query:
        expenses = expenses.filter(description__icontains=query)
    if cat_filter:
        expenses = expenses.filter(category=cat_filter)
    if status_filter:
        expenses = expenses.filter(status=status_filter)
        
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'cat_filter': cat_filter,
        'status_filter': status_filter,
        'categories': Expense.CATEGORY_CHOICES,
        'statuses': Expense.STATUS_CHOICES
    }
    return render(request, 'finance/expense_list.html', context)

@login_required
@staff_only
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            # Super Admins and School Admins can auto-approve their own expenses!
            if request.user.is_school_admin() or request.user.is_superuser:
                expense.status = 'APPROVED'
                expense.approved_by = request.user
                
            with transaction.atomic():
                expense.save()
                
                # If auto-approved, log in cashbook immediately
                if expense.status == 'APPROVED':
                    payment_mode = request.POST.get('payment_mode', 'CASH')
                    pmode = 'BANK' if payment_mode != 'CASH' else 'CASH'
                    
                    CashBookEntry.create_entry(
                        entry_date=expense.expense_date,
                        entry_type='CREDIT',
                        category='EXPENSE',
                        amount=expense.amount,
                        payment_mode=pmode,
                        reference_id=str(expense.id),
                        description=f"Expense: {expense.get_category_display()} - {expense.description}",
                        user=request.user
                    )
            
            log_activity(request.user, "CREATE_EXPENSE", {"category": expense.category, "amount": str(expense.amount), "status": expense.status}, request)
            messages.success(request, f"Expense recorded successfully. Status: {expense.get_status_display()}")
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'finance/expense_form.html', {'form': form, 'title': 'Record New Expense'})

@login_required
@admin_only
def expense_approve(request, pk):
    expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
    if expense.status != 'PENDING':
        messages.warning(request, "This expense has already been processed.")
        return redirect('expense_list')
        
    if request.method == 'POST':
        payment_mode = request.POST.get('payment_mode', 'CASH')
        action = request.POST.get('action', 'APPROVE')
        
        with transaction.atomic():
            if action == 'APPROVE':
                expense.status = 'APPROVED'
                expense.approved_by = request.user
                expense.save()
                
                # Create Cashbook entry
                pmode = 'BANK' if payment_mode != 'CASH' else 'CASH'
                CashBookEntry.create_entry(
                    entry_date=expense.expense_date,
                    entry_type='CREDIT',
                    category='EXPENSE',
                    amount=expense.amount,
                    payment_mode=pmode,
                    reference_id=str(expense.id),
                    description=f"Expense Approved: {expense.get_category_display()} - {expense.description}",
                    user=request.user
                )
                messages.success(request, f"Expense approved and debited from {pmode}.")
            else:
                expense.status = 'REJECTED'
                expense.save()
                messages.success(request, "Expense rejected.")
                
        log_activity(request.user, "PROCESS_EXPENSE", {"id": expense.id, "status": expense.status}, request)
        return redirect('expense_list')
        
    return render(request, 'finance/expense_approve.html', {'expense': expense})

@login_required
@admin_only
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
    if request.method == 'POST':
        expense.delete()
        log_activity(request.user, "DELETE_EXPENSE", {"id": expense.id}, request)
        messages.success(request, "Expense record soft-deleted.")
        return redirect('expense_list')
    return render(request, 'academics/confirm_delete.html', {'obj': expense, 'title': 'Delete Expense Record'})

# Income views
@login_required
@accountant_only
def income_list(request):
    query = request.GET.get('q', '')
    src_filter = request.GET.get('source', '')
    
    incomes = Income.objects.filter(is_deleted=False)
    
    if query:
        incomes = incomes.filter(description__icontains=query)
    if src_filter:
        incomes = incomes.filter(source=src_filter)
        
    paginator = Paginator(incomes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'src_filter': src_filter,
        'sources': Income.SOURCE_CHOICES
    }
    return render(request, 'finance/income_list.html', context)

@login_required
@accountant_only
def income_create(request):
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        payment_mode = request.POST.get('payment_mode', 'CASH')
        
        if form.is_valid():
            with transaction.atomic():
                income = form.save(commit=False)
                income.recorded_by = request.user
                income.save()
                
                # Create Cashbook entry (DEBIT)
                pmode = 'BANK' if payment_mode != 'CASH' else 'CASH'
                CashBookEntry.create_entry(
                    entry_date=income.income_date,
                    entry_type='DEBIT',
                    category='INCOME',
                    amount=income.amount,
                    payment_mode=pmode,
                    reference_id=str(income.id),
                    description=f"Non-fee Income: {income.get_source_display()} - {income.description}",
                    user=request.user
                )
            log_activity(request.user, "CREATE_INCOME", {"source": income.source, "amount": str(income.amount)}, request)
            messages.success(request, "Non-fee income logged successfully.")
            return redirect('income_list')
    else:
        form = IncomeForm()
    return render(request, 'finance/income_form.html', {'form': form, 'title': 'Log Non-Fee Income'})

# Cashbook & Daybook Ledgers
@login_required
@accountant_only
def daybook(request):
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = now().date()
    else:
        target_date = now().date()
        
    # Calculate opening balance: sum of all transactions before target_date
    prior_entries = CashBookEntry.objects.filter(entry_date__lt=target_date, is_deleted=False)
    
    # Simple accumulation logic
    opening_cash = 0.00
    opening_bank = 0.00
    for entry in prior_entries:
        amt = float(entry.amount)
        if entry.entry_type == 'DEBIT':
            if entry.payment_mode == 'CASH':
                opening_cash += amt
            else:
                opening_bank += amt
        else: # CREDIT
            if entry.payment_mode == 'CASH':
                opening_cash -= amt
            else:
                opening_bank -= amt
                
    # Fetch entries of today
    day_entries = CashBookEntry.objects.filter(entry_date=target_date, is_deleted=False).select_related('recorded_by')
    
    # Calculate daily totals
    debits_cash = sum(float(e.amount) for e in day_entries if e.entry_type == 'DEBIT' and e.payment_mode == 'CASH')
    debits_bank = sum(float(e.amount) for e in day_entries if e.entry_type == 'DEBIT' and e.payment_mode == 'BANK')
    credits_cash = sum(float(e.amount) for e in day_entries if e.entry_type == 'CREDIT' and e.payment_mode == 'CASH')
    credits_bank = sum(float(e.amount) for e in day_entries if e.entry_type == 'CREDIT' and e.payment_mode == 'BANK')
    
    closing_cash = opening_cash + debits_cash - credits_cash
    closing_bank = opening_bank + debits_bank - credits_bank
    
    context = {
        'target_date': target_date,
        'opening_cash': opening_cash,
        'opening_bank': opening_bank,
        'day_entries': day_entries,
        'debits_cash': debits_cash,
        'debits_bank': debits_bank,
        'credits_cash': credits_cash,
        'credits_bank': credits_bank,
        'closing_cash': closing_cash,
        'closing_bank': closing_bank
    }
    return render(request, 'finance/daybook.html', context)

@login_required
@accountant_only
def cashbook_ledger(request):
    mode_filter = request.GET.get('mode', '') # CASH / BANK
    cat_filter = request.GET.get('category', '')
    
    entries = CashBookEntry.objects.filter(is_deleted=False).order_by('-entry_date', '-id')
    
    if mode_filter:
        entries = entries.filter(payment_mode=mode_filter)
    if cat_filter:
        entries = entries.filter(category=cat_filter)
        
    paginator = Paginator(entries, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Fetch latest running totals
    latest_entry = CashBookEntry.objects.filter(is_deleted=False).order_by('-entry_date', '-id').first()
    cash_in_hand = latest_entry.running_cash_balance if latest_entry else 0.00
    bank_balance = latest_entry.running_bank_balance if latest_entry else 0.00
    
    context = {
        'page_obj': page_obj,
        'mode_filter': mode_filter,
        'cat_filter': cat_filter,
        'categories': CashBookEntry.CATEGORY_CHOICES,
        'cash_in_hand': cash_in_hand,
        'bank_balance': bank_balance
    }
    return render(request, 'finance/cashbook.html', context)
