#!/usr/bin/env python3
"""Export the full Beancount ledger to accountant-friendly CSV files."""

from __future__ import annotations

import csv
import hashlib
from decimal import Decimal
from pathlib import Path
from typing import Any

from beancount import loader
from beancount.core import data


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger/main.beancount"
OUTPUT_DIR = ROOT / "output/csv"
POSTINGS_CSV = OUTPUT_DIR / "whole-ledger-postings.csv"
TRANSACTIONS_CSV = OUTPUT_DIR / "whole-ledger-transactions.csv"

COMMON_META_KEYS = [
    "source",
    "fichier_source",
    "ligne",
    "document",
    "document_fiscal_id",
    "document_kind",
    "pricing_mode",
    "traitement_taxes_revenu",
    "traitement_taxes_depense",
    "normalisation_revenu",
    "periode_service",
    "ref_paiement",
    "ref_transaction",
    "note",
]


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (set, frozenset, list, tuple)):
        return ";".join(str(item) for item in sorted(value))
    return str(value)


def number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def amount_number(amount: Any) -> str:
    if amount is None:
        return ""
    return number(getattr(amount, "number", ""))


def amount_currency(amount: Any) -> str:
    if amount is None:
        return ""
    return text(getattr(amount, "currency", ""))


def source_path(meta: dict[str, Any]) -> str:
    filename = meta.get("filename")
    if not filename:
        return ""
    try:
        return str(Path(filename).resolve().relative_to(ROOT))
    except ValueError:
        return str(filename)


def txn_id(entry: data.Transaction) -> str:
    raw = "|".join(
        [
            entry.date.isoformat(),
            text(entry.payee),
            text(entry.narration),
            text(entry.meta.get("filename")),
            text(entry.meta.get("lineno")),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def export() -> None:
    entries, errors, _options = loader.load_file(str(LEDGER))
    if errors:
        formatted = "\n".join(str(error) for error in errors)
        raise SystemExit(f"Ledger has validation errors; CSV not generated.\n{formatted}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    transaction_rows: list[dict[str, str]] = []
    posting_rows: list[dict[str, str]] = []

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue

        identifier = txn_id(entry)
        source = source_path(entry.meta)
        source_line = text(entry.meta.get("lineno"))
        meta_values = {key: text(entry.meta.get(key)) for key in COMMON_META_KEYS}

        debit_total = Decimal("0")
        credit_total = Decimal("0")
        accounts: list[str] = []

        for posting_index, posting in enumerate(entry.postings, start=1):
            units = posting.units
            units_number = getattr(units, "number", None)
            if units_number is not None:
                if units_number >= 0:
                    debit_total += units_number
                else:
                    credit_total += -units_number
            accounts.append(posting.account)

            cost = posting.cost
            price = posting.price
            posting_rows.append(
                {
                    "transaction_id": identifier,
                    "date": entry.date.isoformat(),
                    "flag": text(entry.flag),
                    "payee": text(entry.payee),
                    "narration": text(entry.narration),
                    "tags": text(entry.tags),
                    "links": text(entry.links),
                    "source_file": source,
                    "source_line": source_line,
                    **meta_values,
                    "posting_index": str(posting_index),
                    "account": posting.account,
                    "units_number": amount_number(units),
                    "units_currency": amount_currency(units),
                    "cost_number": number(getattr(cost, "number", "")),
                    "cost_currency": text(getattr(cost, "currency", "")),
                    "price_number": amount_number(price),
                    "price_currency": amount_currency(price),
                    "posting_flag": text(posting.flag),
                    "posting_meta": ";".join(
                        f"{key}={value}" for key, value in sorted((posting.meta or {}).items())
                    ),
                }
            )

        transaction_rows.append(
            {
                "transaction_id": identifier,
                "date": entry.date.isoformat(),
                "flag": text(entry.flag),
                "payee": text(entry.payee),
                "narration": text(entry.narration),
                "tags": text(entry.tags),
                "links": text(entry.links),
                "source_file": source,
                "source_line": source_line,
                **meta_values,
                "accounts": ";".join(accounts),
                "posting_count": str(len(entry.postings)),
                "debit_total": number(debit_total),
                "credit_total": number(credit_total),
            }
        )

    transaction_headers = [
        "transaction_id",
        "date",
        "flag",
        "payee",
        "narration",
        "tags",
        "links",
        "source_file",
        "source_line",
        *COMMON_META_KEYS,
        "accounts",
        "posting_count",
        "debit_total",
        "credit_total",
    ]
    posting_headers = [
        "transaction_id",
        "date",
        "flag",
        "payee",
        "narration",
        "tags",
        "links",
        "source_file",
        "source_line",
        *COMMON_META_KEYS,
        "posting_index",
        "account",
        "units_number",
        "units_currency",
        "cost_number",
        "cost_currency",
        "price_number",
        "price_currency",
        "posting_flag",
        "posting_meta",
    ]

    with TRANSACTIONS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=transaction_headers)
        writer.writeheader()
        writer.writerows(transaction_rows)

    with POSTINGS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=posting_headers)
        writer.writeheader()
        writer.writerows(posting_rows)

    print(f"Wrote {len(transaction_rows)} transactions to {TRANSACTIONS_CSV}")
    print(f"Wrote {len(posting_rows)} postings to {POSTINGS_CSV}")


if __name__ == "__main__":
    export()
