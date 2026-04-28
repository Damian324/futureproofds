import pandas as pd
import numpy as np
import uuid
import hashlib
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

N = 5000
START_DATE = datetime(2024, 4, 28) 
END_DATE = datetime(2025, 4, 28)

# --- Shared lookup values -----
PLAN_CODES = [
    "optimize_2024_monthly", "optimize_2024_annual", "launch_2024_monthly",
    "launch_2024_annual", "smart_2024_monthly", "smart_2024_annual",
    "essential_2024_monthly", "essential_2024_annual", "agency_2024_monthly"
]
PLAN_NAMES = ["Optimize", "Launch", "Smart", "Essential", "Agency"]
PLAN_ASSISTANCE_LEVELS = ["SelfServe", "Assisted", "Managed"]
PLAN_GROUPS = ["monthly_core", "annual_core", "monthly_agency", "annual_agency"]
PLAN_INTERVALS = ["monthly_core", "annual_core"]
BILLING_SOURCES = ["recurly", "stripe"]
PRODUCTS = ["core", "agency"]
CURRENCIES = ["USD", "CAD", "EUR", "GBP", "AUD"]
COUNTRIES = ["United States", "Canada", "United Kingdom", "Australia", "Germany", "France", "Brazil", "Mexico"]
CONTINENTS = ["NA", "EU", "SA", "OC"]
BUSINESS_SIZES = ["small", "medium", "large", "enterprise"]
INDUSTRIES = ["marketing", "ecommerce", "saas", "agency", "retail", "finance", "healthcare"]
SEGMENTS = ["smb", "mid-market", "enterprise"]
PERSONAS = ["creator", "marketer", "developer", "analyst"]
EXPERIENCES = ["beginner", "intermediate", "advanced"]
BENEFITS = ["conversion", "traffic", "leads", "brand"]
PREV_PAYING_STATUSES = ["Paying", "Not Paying"]

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def random_hex(length=16):
    return ''.join(random.choices('0123456789abcdef', k=length))

def random_uuid():
    return str(uuid.uuid4())

def md5_key(*args):
    val = ''.join(str(a) for a in args)
    return hashlib.md5(val.encode()).hexdigest()

def random_revenue(low=0, high=500, null_prob=0.4):
    if random.random() < null_prob:
        return np.nan
    return round(random.uniform(low, high), 2)

def random_flag(true_prob=0.3, null_prob=0.2):
    if random.random() < null_prob:
        return np.nan
    return 1.0 if random.random() < true_prob else 0.0

def random_plan_price():
    return random.choice([49.0, 79.0, 99.0, 149.0, 199.0, 249.0, 299.0, 399.0, 499.0])

# Generate shared account pool so accounts appear multiple times (realistic)
NUM_ACCOUNTS = 800
accounts = [{
    "billing_account_id": random_hex(16),
    "account_id": random.randint(100000, 9999999),
    "account_uuid": random_uuid(),
    "account_unique_key": random_hex(32),
    "partner_uuid": np.nan if random.random() < 0.85 else random_uuid(),
    "plan_code": random.choice(PLAN_CODES),
    "plan_monthly_price": random_plan_price(),
    "plan_assistance_level": random.choice(PLAN_ASSISTANCE_LEVELS),
    "plan_group": random.choice(PLAN_GROUPS),
    "plan_interval": random.choice(PLAN_INTERVALS),
    "plan_name": random.choice(PLAN_NAMES),
    "billing_source": random.choice(BILLING_SOURCES),
    "product": random.choice(PRODUCTS),
    "currency": random.choice(CURRENCIES),
    "country_name_asnow": random.choice(COUNTRIES),
    "continent_asnow": random.choice(CONTINENTS),
    "business_size": random.choice(BUSINESS_SIZES),
    "industry": random.choice(INDUSTRIES),
    "unbounce_segment": random.choice(SEGMENTS),
    "creator_persona": random.choice(PERSONAS),
    "creator_experience": random.choice(EXPERIENCES),
    "expected_benefit": random.choice(BENEFITS),
    "all_segments": random.choice(SEGMENTS),
    "first_touch_product": random.choice(PRODUCTS),
    "last_touch_product": random.choice(PRODUCTS),
    "phishing_rating": round(random.uniform(0, 5), 2),
    "is_phishing_account": random.random() < 0.02,
} for _ in range(NUM_ACCOUNTS)]

# ============================================================
# DAILY CSV
# ============================================================
print("Generating daily CSV...")
daily_rows = []
for i in range(N):
    acc = random.choice(accounts)
    interval_start = random_date(START_DATE, END_DATE - timedelta(days=1))
    interval_end = interval_start + timedelta(days=1)
    adj_billing = interval_start - timedelta(days=random.randint(0, 15))
    is_nts = random.choice([0, 1])
    is_churned = random_flag(0.05, 0.0)
    churned_recurring = random_flag(0.05, 0.1)
    recurring = random_flag(0.6, 0.05)
    transactional = random_flag(0.3, 0.05)
    first_time_recurring = random_flag(0.1, 0.1)
    reactivated_recurring_customer = random_flag(0.08, 0.1)
    plan_price = acc["plan_monthly_price"]
    prev_plan = random.choice(PLAN_CODES)

    row = {
        "interval_start": interval_start.strftime("%Y-%m-%d"),
        "interval_end": interval_end.strftime("%Y-%m-%d"),
        "adjusted_billing_cycle_start_date": adj_billing.strftime("%Y-%m-%d"),
        "trial_ends_at": np.nan if is_nts == 0 else (interval_start + timedelta(days=14)).strftime("%Y-%m-%d"),
        "grace_period_start_date": np.nan if random.random() < 0.85 else interval_start.strftime("%Y-%m-%d"),
        "grace_period_end_date": np.nan if random.random() < 0.85 else (interval_start + timedelta(days=7)).strftime("%Y-%m-%d"),
        "billing_account_id": acc["billing_account_id"],
        "account_id": acc["account_id"],
        "account_uuid": acc["account_uuid"],
        "account_unique_key": acc["account_unique_key"],
        "partner_uuid": acc["partner_uuid"],
        "is_nts": is_nts,
        "paid": random_flag(0.7, 0.1),
        "paid_revenue": random_revenue(0, plan_price, 0.3),
        "expected_paid_revenue": random_revenue(plan_price * 0.9, plan_price * 1.1, 0.3),
        "transactional": transactional,
        "is_account_new_transactional": random_flag(0.05, 0.2),
        "is_account_new_transactional_2x": random_flag(0.03, 0.2),
        "transactional_revenue": random_revenue(0, plan_price, 0.4) if transactional == 1.0 else np.nan,
        "expected_transactional_revenue": random_revenue(0, plan_price, 0.4),
        "recurring": recurring,
        "recurring_revenue": random_revenue(0, plan_price, 0.3) if recurring == 1.0 else np.nan,
        "non_recurring_revenue": random_revenue(0, 50, 0.6),
        "expected_recurring_revenue": random_revenue(plan_price * 0.8, plan_price, 0.3),
        "reactivated": random_flag(0.05, 0.1),
        "first_time_recurring": first_time_recurring,
        "reactivated_first_time_recurring": random_flag(0.03, 0.2),
        "newly_reactivated_recurring_customer": random_flag(0.04, 0.2),
        "reactivated_recurring_customer": reactivated_recurring_customer,
        "is_reactivated_new_transactional": random_flag(0.03, 0.2),
        "is_reactivated_new_transactional_2x": random_flag(0.02, 0.2),
        "first_time_churned_recurring": random_flag(0.04, 0.2),
        "first_time_churned_recurring_revenue": random_revenue(0, plan_price, 0.7),
        "expected_first_time_churned_recurring_revenue": random_revenue(0, plan_price, 0.7),
        "is_churned": is_churned,
        "churned_recurring": churned_recurring,
        "churned_recurring_revenue": random_revenue(0, plan_price, 0.7) if churned_recurring == 1.0 else np.nan,
        "churned_transactional_revenue": random_revenue(0, plan_price, 0.8),
        "churned_non_recurring_revenue": random_revenue(0, 50, 0.8),
        "expected_churned_recurring_revenue": random_revenue(0, plan_price, 0.7),
        "lost_recurring_revenue": random_revenue(0, plan_price, 0.7) if is_churned == 1.0 else np.nan,
        "times_churned": random.choice([np.nan, 0.0, 1.0, 2.0, 3.0]),
        "expanded_recurring_revenue": random_revenue(0, 100, 0.75),
        "contracted_recurring_revenue": random_revenue(-200, 0, 0.75),
        "contracted_recurring_realized_revenue": random_revenue(-200, 0, 0.75),
        "tenure": random.choice([np.nan] + list(range(1, 60))),
        "current_lifecycle_tenure": random.choice([np.nan] + list(range(1, 36))),
        "subscription_length": random.choice([np.nan] + list(range(1, 48))),
        "current_lifecycle_subscription_length": random.choice([np.nan] + list(range(1, 24))),
        "nrr_cohort_flag": random_flag(0.5, 0.3),
        "new_trial": random_flag(0.1, 0.5) if is_nts == 1 else np.nan,
        "reactivated_trial": random_flag(0.05, 0.5) if is_nts == 1 else np.nan,
        "is_first_day_of_trial": random_flag(0.1, 0.5) if is_nts == 1 else np.nan,
        "paid_conversion": random_flag(0.05, 0.5) if is_nts == 1 else np.nan,
        "paid_2x_conversion": random_flag(0.03, 0.5) if is_nts == 1 else np.nan,
        "recurring_conversion": random_flag(0.04, 0.5) if is_nts == 1 else np.nan,
        "net_paid_conversion": random_flag(0.05, 0.5) if is_nts == 1 else np.nan,
        "net_paid_2x_conversion": random_flag(0.03, 0.5) if is_nts == 1 else np.nan,
        "net_recurring_conversion": random_flag(0.04, 0.5) if is_nts == 1 else np.nan,
        "is_reverse_trial_subscription": random.choice([0, 1]),
        "is_started_from_reverse_trial": random.choice([0, 1]),
        "is_reverse_trial_grace_period": random.choice([0, 1]),
        "is_reverse_trial_currently_in_grace_period": random_flag(0.05, 0.3),
        "prev_month_paid_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_paid_recurring_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_recurring_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_paid_non_recurring_revenue": random_revenue(0, 50, 0.6),
        "prev_month_non_recurring_revenue": random_revenue(0, 50, 0.6),
        "prev_month_plan_code": prev_plan,
        "prev_month_plan_assistance_level": random.choice(PLAN_ASSISTANCE_LEVELS),
        "prev_month_plan_price_per_month": random_plan_price(),
        "phishing_rating": acc["phishing_rating"],
        "is_phishing_account": acc["is_phishing_account"],
        "all_segments": acc["all_segments"],
        "billing_source": acc["billing_source"],
        "product": acc["product"],
        "currency": acc["currency"],
        "is_crossover": random.choice([0, 1]),
        "first_touch_product": acc["first_touch_product"],
        "last_touch_product": acc["last_touch_product"],
        "country_name_asnow": acc["country_name_asnow"],
        "continent_asnow": acc["continent_asnow"],
        "business_size": acc["business_size"],
        "industry": acc["industry"],
        "unbounce_segment": acc["unbounce_segment"],
        "creator_persona": acc["creator_persona"],
        "creator_experience": acc["creator_experience"],
        "expected_benefit": acc["expected_benefit"],
        "plan_code": acc["plan_code"],
        "plan_interval": acc["plan_interval"],
        "plan_assistance_level": acc["plan_assistance_level"],
        "plan_group": acc["plan_group"],
        "plan_pricing_year": random.choice([2023.0, 2024.0, 2025.0]),
        "plan_monthly_price": plan_price,
        "is_free_plan_code_trial": 0,
        "plan_name": acc["plan_name"],
        "unique_key": md5_key(interval_start, acc["account_unique_key"], is_nts),
    }
    daily_rows.append(row)

daily_df = pd.DataFrame(daily_rows)
daily_df.to_csv("keysaas_daily_dummy.csv", index=False)
print(f"Daily CSV saved: {len(daily_df)} rows x {len(daily_df.columns)} columns")

# ============================================================
# MONTHLY CSV
# ============================================================
print("Generating monthly CSV...")
monthly_rows = []
for i in range(N):
    acc = random.choice(accounts)
    month_start = START_DATE.replace(day=1) + timedelta(days=30 * random.randint(0, 11))
    month_start = month_start.replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1)
    first_billing = month_start - timedelta(days=random.randint(0, 10))
    is_nts = random.choice([0, 1])
    is_churned = random_flag(0.05, 0.0)
    churned_recurring = random_flag(0.05, 0.1)
    recurring = random_flag(0.6, 0.05)
    transactional = random_flag(0.3, 0.05)
    plan_price = acc["plan_monthly_price"]
    prev_plan = random.choice(PLAN_CODES)

    row = {
        "interval_start": month_start.strftime("%Y-%m-%d"),
        "interval_end": month_end.strftime("%Y-%m-%d"),
        "billing_account_id": acc["billing_account_id"],
        "account_id": acc["account_id"],
        "account_uuid": acc["account_uuid"],
        "account_unique_key": acc["account_unique_key"],
        "partner_uuid": acc["partner_uuid"],
        "is_nts": is_nts,
        "first_billing_cycle_date": first_billing.strftime("%Y-%m-%d"),
        "grace_period_start_date": np.nan if random.random() < 0.85 else month_start.strftime("%Y-%m-%d"),
        "grace_period_end_date": np.nan if random.random() < 0.85 else (month_start + timedelta(days=7)).strftime("%Y-%m-%d"),
        "paid": random_flag(0.7, 0.1),
        "paid_revenue": random_revenue(0, plan_price * 1.2, 0.3),
        "expected_paid_revenue": random_revenue(plan_price * 0.9, plan_price * 1.1, 0.3),
        "transactional": transactional,
        "is_account_new_transactional": random_flag(0.05, 0.2),
        "is_account_new_transactional_2x": random_flag(0.03, 0.2),
        "transactional_revenue": random_revenue(0, plan_price, 0.4) if transactional == 1.0 else np.nan,
        "expected_transactional_revenue": random_revenue(0, plan_price, 0.4),
        "recurring": recurring,
        "recurring_revenue": random_revenue(0, plan_price * 1.2, 0.3) if recurring == 1.0 else np.nan,
        "non_recurring_revenue": random_revenue(0, 100, 0.6),
        "expected_recurring_revenue": random_revenue(plan_price * 0.8, plan_price, 0.3),
        "reactivated": random_flag(0.05, 0.1),
        "first_time_recurring": random_flag(0.1, 0.1),
        "reactivated_first_time_recurring": random_flag(0.03, 0.2),
        "newly_reactivated_recurring_customer": random_flag(0.04, 0.2),
        "reactivated_recurring_customer": random_flag(0.08, 0.1),
        "is_reactivated_new_transactional": random_flag(0.03, 0.2),
        "is_reactivated_new_transactional_2x": random_flag(0.02, 0.2),
        "first_time_churned_recurring": random_flag(0.04, 0.2),
        "first_time_churned_recurring_revenue": random_revenue(0, plan_price, 0.7),
        "expected_first_time_churned_recurring_revenue": random_revenue(0, plan_price, 0.7),
        "is_churned": is_churned,
        "churned_recurring": churned_recurring,
        "churned_recurring_revenue": random_revenue(0, plan_price, 0.7) if churned_recurring == 1.0 else np.nan,
        "churned_transactional_revenue": random_revenue(0, plan_price, 0.8),
        "churned_non_recurring_revenue": random_revenue(0, 50, 0.8),
        "expected_churned_recurring_revenue": random_revenue(0, plan_price, 0.7),
        "lost_recurring_revenue": random_revenue(0, plan_price, 0.7) if is_churned == 1.0 else np.nan,
        "times_churned": random.choice([np.nan, 0.0, 1.0, 2.0, 3.0]),
        "expanded_recurring_revenue": random_revenue(0, 150, 0.75),
        "contracted_recurring_revenue": random_revenue(-300, 0, 0.75),
        "contracted_recurring_realized_revenue": random_revenue(-300, 0, 0.75),
        "tenure": random.choice([np.nan] + list(range(1, 60))),
        "current_lifecycle_tenure": random.choice([np.nan] + list(range(1, 36))),
        "subscription_length": random.choice([np.nan] + list(range(1, 48))),
        "current_lifecycle_subscription_length": random.choice([np.nan] + list(range(1, 24))),
        "nrr_cohort_flag": random_flag(0.5, 0.3),
        "new_trial": random_flag(0.1, 0.5) if is_nts == 1 else np.nan,
        "reactivated_trial": random_flag(0.05, 0.5) if is_nts == 1 else np.nan,
        "paid_conversion": random_flag(0.05, 0.5) if is_nts == 1 else np.nan,
        "paid_2x_conversion": random_flag(0.03, 0.5) if is_nts == 1 else np.nan,
        "recurring_conversion": random_flag(0.04, 0.5) if is_nts == 1 else np.nan,
        "net_paid_conversion": random_flag(0.05, 0.5) if is_nts == 1 else np.nan,
        "net_paid_2x_conversion": random_flag(0.03, 0.5) if is_nts == 1 else np.nan,
        "net_recurring_conversion": random_flag(0.04, 0.5) if is_nts == 1 else np.nan,
        "is_reverse_trial_subscription": random_flag(0.1, 0.1),
        "is_started_from_reverse_trial": random_flag(0.1, 0.1),
        "is_reverse_trial_grace_period": random_flag(0.05, 0.1),
        "is_reverse_trial_currently_in_grace_period": random_flag(0.05, 0.3),
        "prev_month_paid_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_paid_recurring_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_recurring_revenue": random_revenue(0, plan_price, 0.4),
        "prev_month_paid_non_recurring_revenue": random_revenue(0, 50, 0.6),
        "prev_month_non_recurring_revenue": random_revenue(0, 50, 0.6),
        "phishing_rating": acc["phishing_rating"],
        "is_phishing_account": acc["is_phishing_account"],
        "all_segments": acc["all_segments"],
        "billing_source": acc["billing_source"],
        "product": acc["product"],
        "currency": acc["currency"],
        "is_crossover": random.choice([0, 1]),
        "first_touch_product": acc["first_touch_product"],
        "last_touch_product": acc["last_touch_product"],
        "country_name_asnow": acc["country_name_asnow"],
        "continent_asnow": acc["continent_asnow"],
        "business_size": acc["business_size"],
        "industry": acc["industry"],
        "unbounce_segment": acc["unbounce_segment"],
        "creator_persona": acc["creator_persona"],
        "creator_experience": acc["creator_experience"],
        "expected_benefit": acc["expected_benefit"],
        "plan_code": acc["plan_code"],
        "plan_monthly_price": plan_price,
        "plan_interval": acc["plan_interval"],
        "plan_assistance_level": acc["plan_assistance_level"],
        "plan_group": acc["plan_group"],
        "plan_pricing_year": random.choice([2023.0, 2024.0, 2025.0]),
        "plan_name": acc["plan_name"],
        "prev_month_plan_code": prev_plan,
        "prev_month_paying_status": random.choice(PREV_PAYING_STATUSES),
        "prev_month_plan_assistance_level": random.choice(PLAN_ASSISTANCE_LEVELS),
        "prev_month_plan_price_per_month": random_plan_price(),
        "unique_key": md5_key(month_start, acc["account_unique_key"], is_nts),
    }
    monthly_rows.append(row)

monthly_df = pd.DataFrame(monthly_rows)
monthly_df.to_csv("keysaas_monthly_dummy.csv", index=False)
print(f"Monthly CSV saved: {len(monthly_df)} rows x {len(monthly_df.columns)} columns")
print("Done!")