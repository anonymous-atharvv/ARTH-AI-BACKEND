# backend/ai/upi_parser.py
"""Parse UPI screenshot/statement data."""
import re, structlog
from typing import Optional, List

logger = structlog.get_logger()

def parse_upi_text(text: str) -> List[dict]:
    """Extract UPI transactions from OCR text of a UPI statement screenshot."""
    transactions = []
    lines = text.strip().split("\n")
    for line in lines:
        amount_match = re.search(r'₹\s*([\d,]+(?:\.\d{2})?)', line)
        if not amount_match:
            continue
        amount = float(amount_match.group(1).replace(",", ""))
        tx_type = "expense" if any(w in line.lower() for w in ["paid", "sent", "debited"]) else "income"
        upi_id = re.search(r'[\w.]+@[\w]+', line)
        transactions.append({
            "amount": amount, "type": tx_type,
            "counterparty": upi_id.group(0) if upi_id else "UPI Transaction",
            "payment_method": "upi", "source": "upi_statement",
        })
    return transactions
