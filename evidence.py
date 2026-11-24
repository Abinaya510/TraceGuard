def build_transaction_index(transactions):
    """
    Create a lookup table using transaction_id.
    """

    return {
        tx["transaction_id"]: tx
        for tx in transactions
    }


def build_evidence(signals, transactions):
    """
    Attach the original transaction records to every risk signal.

    This guarantees that every investigation finding can be traced
    directly back to the customer's input transaction history.
    """

    transaction_index = build_transaction_index(transactions)

    evidence = []

    for signal in signals:

        cited_transactions = []

        for transaction_id in signal["transaction_ids"]:

            transaction = transaction_index.get(transaction_id)

            if transaction is None:
                continue

            cited_transactions.append(
                {
                    "transaction_id": transaction["transaction_id"],
                    "date": transaction["date"],
                    "description": transaction["description"],
                    "payee": transaction["payee"],
                    "amount": float(transaction["amount"]),
                    "channel": transaction["channel"],
                }
            )

        evidence.append(
            {
                "rule": signal["rule"],
                "severity": signal["severity"],
                "explanation": signal["explanation"],
                "transactions": cited_transactions,
            }
        )

    return evidence