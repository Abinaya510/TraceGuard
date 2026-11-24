import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median


@dataclass
class RiskSignal:
    rule: str
    severity: str
    transaction_ids: list
    explanation: str


# -------------------------------------------------
# Load rule configuration
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_FILE = BASE_DIR / "data" / "risk_rules.json"


def load_risk_rules():
    """
    Load deterministic risk rules from the local configuration file.
    """

    with open(RULES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


RULE_CONFIG = load_risk_rules()


# -------------------------------------------------
# Utility functions
# -------------------------------------------------

def parse_datetime(value):
    return datetime.strptime(
        value,
        "%Y-%m-%d %H:%M:%S"
    )


# -------------------------------------------------
# Customer behaviour profile
# -------------------------------------------------

def calculate_customer_profile(transactions):
    """
    Build the customer's normal spending profile.

    Salary transactions are excluded because they represent recurring
    income rather than discretionary spending.

    CARD and UPI transactions are used as the normal spending baseline.
    """

    baseline_amounts = []

    for tx in transactions:

        try:
            amount = float(tx["amount"])
        except (ValueError, TypeError):
            continue

        description = str(
            tx["description"]
        ).lower()

        channel = str(
            tx["channel"]
        ).upper()

        # Salary is a legitimate recurring income pattern.
        if "salary" in description:
            continue

        # Everyday CARD and UPI transactions represent
        # the normal spending baseline.
        if channel in {"CARD", "UPI"}:
            baseline_amounts.append(amount)

    return {
        "median_amount": (
            median(baseline_amounts)
            if baseline_amounts
            else 0
        )
    }


# -------------------------------------------------
# Rule 1: Large transfer
# -------------------------------------------------

def detect_large_transfers(transactions, profile):
    """
    Detect transactions substantially larger than normal spending.
    """

    signals = []

    median_amount = profile["median_amount"]

    if median_amount <= 0:
        return signals

    rule_config = RULE_CONFIG["rules"]["LARGE_TRANSFER"]

    multiplier = rule_config["threshold_multiplier"]

    threshold = median_amount * multiplier

    for tx in transactions:

        try:
            amount = float(tx["amount"])
        except (ValueError, TypeError):
            continue

        description = str(
            tx["description"]
        ).lower()

        # Salary is established income.
        if "salary" in description:
            continue

        if amount >= threshold:

            signals.append(
                RiskSignal(
                    rule="LARGE_TRANSFER",
                    severity=rule_config["severity"],
                    transaction_ids=[
                        tx["transaction_id"]
                    ],
                    explanation=(
                        f"Transaction amount ₹{amount:,.2f} is "
                        f"unusually large compared with the "
                        f"customer's typical spending amount "
                        f"of approximately ₹{median_amount:,.2f}."
                    ),
                )
            )

    return signals


# -------------------------------------------------
# Rule 2: New payee burst
# -------------------------------------------------

def detect_new_payee_bursts(transactions):
    """
    Detect multiple transactions to a previously unseen payee
    within the configured time window.
    """

    signals = []

    rule_config = RULE_CONFIG["rules"]["NEW_PAYEE_BURST"]

    window_minutes = rule_config["window_minutes"]

    minimum_transactions = rule_config[
        "minimum_transactions"
    ]

    sorted_transactions = sorted(
        transactions,
        key=lambda tx: parse_datetime(tx["date"])
    )

    seen_payees = set()

    for i, current in enumerate(sorted_transactions):

        payee = current["payee"]

        # Already established payee.
        if payee in seen_payees:
            continue

        current_time = parse_datetime(
            current["date"]
        )

        burst = [current]

        for candidate in sorted_transactions[i + 1:]:

            if candidate["payee"] != payee:
                continue

            candidate_time = parse_datetime(
                candidate["date"]
            )

            difference = (
                candidate_time - current_time
            )

            if difference <= timedelta(
                minutes=window_minutes
            ):
                burst.append(candidate)

        if len(burst) >= minimum_transactions:

            signals.append(
                RiskSignal(
                    rule="NEW_PAYEE_BURST",
                    severity=rule_config["severity"],
                    transaction_ids=[
                        tx["transaction_id"]
                        for tx in burst
                    ],
                    explanation=(
                        f"{minimum_transactions} or more transactions "
                        f"were made to the previously unseen payee "
                        f"'{payee}' within {window_minutes} minutes."
                    ),
                )
            )

        # The payee becomes established after its first appearance.
        seen_payees.add(payee)

    return signals


# -------------------------------------------------
# Rule 3: Odd-hour activity
# -------------------------------------------------

def detect_odd_hours(transactions):
    """
    Detect transactions occurring during the configured
    unusual activity window.
    """

    signals = []

    rule_config = RULE_CONFIG["rules"]["ODD_HOUR"]

    start_hour = rule_config["start_hour"]
    end_hour = rule_config["end_hour"]

    for tx in transactions:

        dt = parse_datetime(
            tx["date"]
        )

        if start_hour <= dt.hour < end_hour:

            signals.append(
                RiskSignal(
                    rule="ODD_HOUR",
                    severity=rule_config["severity"],
                    transaction_ids=[
                        tx["transaction_id"]
                    ],
                    explanation=(
                        f"Transaction occurred at "
                        f"{dt.strftime('%H:%M')}, within the "
                        f"defined unusual activity window "
                        f"({start_hour:02d}:00–{end_hour - 1:02d}:59)."
                    ),
                )
            )

    return signals


# -------------------------------------------------
# Rule 4: Pattern deviation
# -------------------------------------------------

def detect_pattern_deviation(transactions, profile):
    """
    Detect transactions that substantially break the customer's
    established spending pattern.
    """

    signals = []

    median_amount = profile["median_amount"]

    if median_amount <= 0:
        return signals

    rule_config = RULE_CONFIG["rules"]["PATTERN_DEVIATION"]

    multiplier = rule_config["threshold_multiplier"]

    deviation_threshold = median_amount * multiplier

    for tx in transactions:

        try:
            amount = float(tx["amount"])
        except (ValueError, TypeError):
            continue

        description = str(
            tx["description"]
        ).lower()

        # Salary is established income behaviour.
        if "salary" in description:
            continue

        if amount >= deviation_threshold:

            signals.append(
                RiskSignal(
                    rule="PATTERN_DEVIATION",
                    severity=rule_config["severity"],
                    transaction_ids=[
                        tx["transaction_id"]
                    ],
                    explanation=(
                        f"Transaction differs substantially from "
                        f"the customer's established spending "
                        f"pattern: ₹{amount:,.2f} is more than "
                        f"{multiplier}× the typical spending amount "
                        f"of approximately ₹{median_amount:,.2f}."
                    ),
                )
            )

    return signals


# -------------------------------------------------
# Main analysis
# -------------------------------------------------

def analyze_transactions(transactions):

    profile = calculate_customer_profile(
        transactions
    )

    signals = []

    # Run all deterministic rules.

    signals.extend(
        detect_large_transfers(
            transactions,
            profile
        )
    )

    signals.extend(
        detect_new_payee_bursts(
            transactions
        )
    )

    signals.extend(
        detect_odd_hours(
            transactions
        )
    )

    signals.extend(
        detect_pattern_deviation(
            transactions,
            profile
        )
    )

    # -------------------------------------------------
    # Investigation priority
    # -------------------------------------------------

    score = 0

    priority_config = RULE_CONFIG[
        "investigation_priority"
    ]

    for signal in signals:

        score += priority_config.get(
            signal.severity,
            0
        )

    # Identify independent rules.
    unique_rules = {
        signal.rule
        for signal in signals
    }

    if len(unique_rules) >= 3:

        score += priority_config[
            "multiple_rule_bonus"
        ]

    score = min(
        score,
        priority_config["maximum_score"]
    )

    # -------------------------------------------------
    # Flagged transactions
    # -------------------------------------------------

    flagged_ids = []

    for signal in signals:

        for transaction_id in signal.transaction_ids:

            if transaction_id not in flagged_ids:
                flagged_ids.append(
                    transaction_id
                )

    # -------------------------------------------------
    # Structured result
    # -------------------------------------------------

    return {
        "attention_required": len(signals) > 0,

        "risk_score": score,

        "flagged_transaction_ids": flagged_ids,

        "signals": [
            {
                "rule": signal.rule,
                "severity": signal.severity,
                "transaction_ids": signal.transaction_ids,
                "explanation": signal.explanation,
            }
            for signal in signals
        ],
    }