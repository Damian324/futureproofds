#!/usr/bin/env python3
"""
Load keysaas CSVs into the fpds PostgreSQL database.
Idempotent: drops and recreates both tables on each run.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd

# ── Config ──────────────────────────────────────────────────────────────────
DB_NAME   = "fpds"
DB_USER   = os.getenv("PGUSER", "damian.sanchez")
DB_HOST   = "localhost"
DB_PORT   = 5432
DB_PASS   = ""

DAILY_CSV   = "/Users/damian.sanchez/Desktop/repos/futureproofds/keysaas_daily_dummy.csv"
MONTHLY_CSV = "/Users/damian.sanchez/Desktop/repos/futureproofds/keysaas_monthly_dummy.csv"

# ── Column-type specifications ───────────────────────────────────────────────
# TEXT columns shared by both tables that need explicit handling
TEXT_COLS = {
    "billing_account_id", "account_uuid", "account_unique_key", "partner_uuid",
    "trial_ends_at", "grace_period_start_date", "grace_period_end_date",
    "prev_month_plan_code", "prev_month_plan_assistance_level",
    "prev_month_paying_status",
    "all_segments", "billing_source", "product", "currency",
    "first_touch_product", "last_touch_product",
    "country_name_asnow", "continent_asnow",
    "business_size", "industry", "unbounce_segment",
    "creator_persona", "creator_experience", "expected_benefit",
    "plan_code", "plan_interval", "plan_assistance_level",
    "plan_group", "plan_name",
    "unique_key",
}

DATE_COLS_DAILY = {
    "interval_start", "interval_end", "adjusted_billing_cycle_start_date",
}

DATE_COLS_MONTHLY = {
    "interval_start", "interval_end", "first_billing_cycle_date",
}

# These are INTEGER (not FLOAT) even though they look numeric
INTEGER_COLS = {
    "account_id",
    "is_nts", "is_crossover",
    "is_reverse_trial_subscription", "is_started_from_reverse_trial",
    "is_reverse_trial_grace_period",
    "is_free_plan_code_trial",
}

BOOLEAN_COLS = {"is_phishing_account"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def pg_type(col: str, date_cols: set) -> str:
    """Return the PostgreSQL column type for a given column name."""
    if col in date_cols:
        return "DATE"
    if col in TEXT_COLS:
        return "TEXT"
    if col in BOOLEAN_COLS:
        return "BOOLEAN"
    if col in INTEGER_COLS:
        return "INTEGER"
    return "FLOAT"


def build_create_ddl(table: str, columns: list[str], date_cols: set) -> str:
    col_defs = []
    for col in columns:
        dtype = pg_type(col, date_cols)
        col_defs.append(f'    "{col}" {dtype}')
    col_defs_sql = ",\n".join(col_defs)
    return (
        f'CREATE TABLE public."{table}" (\n'
        f"{col_defs_sql},\n"
        f'    PRIMARY KEY ("unique_key")\n'
        f");"
    )


def create_db_if_missing():
    print(f"[1/5] Ensuring database '{DB_NAME}' exists …")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone():
        print(f"    Database '{DB_NAME}' already exists — skipping create.")
    else:
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"    Created database '{DB_NAME}'.")
    cur.close()
    conn.close()


def load_table(
    conn,
    table: str,
    csv_path: str,
    date_cols: set,
):
    print(f"\n[*] Loading table '{table}' from {csv_path} …")

    # Read CSV — keep everything as strings first so we control casting
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_values=[""])
    print(f"    Read {len(df):,} rows × {len(df.columns)} columns.")

    # Deduplicate on primary key (keep last occurrence)
    before = len(df)
    df = df.drop_duplicates(subset=["unique_key"], keep="last")
    after = len(df)
    if before != after:
        print(f"    Dropped {before - after:,} duplicate unique_key rows → {after:,} distinct rows.")

    cur = conn.cursor()

    # Drop + recreate
    print(f"    Dropping & recreating table …")
    cur.execute(f'DROP TABLE IF EXISTS public."{table}" CASCADE')
    ddl = build_create_ddl(table, list(df.columns), date_cols)
    cur.execute(ddl)

    # Cast columns in the DataFrame before inserting
    for col in df.columns:
        dtype = pg_type(col, date_cols)
        if dtype == "DATE":
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        elif dtype == "BOOLEAN":
            df[col] = df[col].map(
                lambda v: True if str(v).strip().lower() == "true"
                else (False if str(v).strip().lower() == "false" else None)
            )
        elif dtype == "INTEGER":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif dtype == "FLOAT":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        # TEXT — leave as-is (None stays None for NULL)

    # Replace pandas NA with None for psycopg2
    df = df.where(pd.notnull(df), None)

    # Convert numpy/pandas scalar types to native Python so psycopg2 can adapt them
    def to_python(v):
        if v is None:
            return None
        try:
            if pd.isna(v):              # catches pd.NA, np.nan, float('nan')
                return None
        except (TypeError, ValueError):
            pass
        if hasattr(v, "item"):          # numpy scalar
            return v.item()
        return v

    # Batch insert
    cols_quoted = ", ".join(f'"{c}"' for c in df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    insert_sql = (
        f'INSERT INTO public."{table}" ({cols_quoted}) VALUES ({placeholders})'
        f' ON CONFLICT ("unique_key") DO NOTHING'
    )

    BATCH = 500
    total = len(df)
    for i in range(0, total, BATCH):
        batch = df.iloc[i : i + BATCH]
        rows = [tuple(to_python(v) for v in row) for row in batch.itertuples(index=False, name=None)]
        cur.executemany(insert_sql, rows)
        pct = min(i + BATCH, total)
        print(f"    Inserted {pct:,}/{total:,} rows …", end="\r")

    conn.commit()
    print(f"\n    Committed {total:,} rows to '{table}'.")

    # Verify
    cur.execute(f'SELECT COUNT(*) FROM public."{table}"')
    db_count = cur.fetchone()[0]
    print(f"    Verified: {db_count:,} rows in database.")
    cur.close()
    return db_count


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    create_db_if_missing()

    print(f"\n[2/5] Connecting to database '{DB_NAME}' …")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )

    print("\n[3/5] Loading daily table …")
    daily_count = load_table(
        conn, "fct_key_saas_byday", DAILY_CSV, DATE_COLS_DAILY
    )

    print("\n[4/5] Loading monthly table …")
    monthly_count = load_table(
        conn, "fct_key_saas_bymonth", MONTHLY_CSV, DATE_COLS_MONTHLY
    )

    conn.close()

    print("\n" + "=" * 60)
    print("[5/5] SUCCESS SUMMARY")
    print("=" * 60)
    print(f"  fct_key_saas_byday   → {daily_count:,} rows")
    print(f"  fct_key_saas_bymonth → {monthly_count:,} rows")
    print("  (Note: dummy CSVs contain duplicate unique_keys; counts reflect")
    print("   distinct rows after deduplication.)")
    print()
    print("Connection string:")
    print(f"  postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()
