import pandas as pd


REQUIRED_COLUMNS = [
    "transaction_id",
    "date",
    "description",
    "payee",
    "amount",
    "channel",
]


def load_transactions(file_path):
    """
    Load and validate transaction history from a CSV file.
    """

    errors = []

    # Load CSV
    try:
        df = pd.read_csv(file_path)

    except FileNotFoundError:
        return {
            "success": False,
            "transactions": [],
            "errors": ["Transaction file was not found."]
        }

    except Exception as exc:
        return {
            "success": False,
            "transactions": [],
            "errors": [
                f"Unable to read transaction file: {exc}"
            ]
        }

    # Check empty file
    if df.empty:
        return {
            "success": False,
            "transactions": [],
            "errors": ["Transaction file is empty."]
        }

    # Check required columns
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        return {
            "success": False,
            "transactions": [],
            "errors": [
                "Missing required columns: "
                + ", ".join(missing_columns)
            ]
        }

    # Keep required columns
    df = df[REQUIRED_COLUMNS].copy()

    # Validate transaction IDs
    if df["transaction_id"].isna().any():
        errors.append(
            "One or more transactions have a missing transaction_id."
        )

    duplicate_ids = (
        df["transaction_id"]
        .astype(str)
        .duplicated()
    )

    if duplicate_ids.any():
        errors.append(
            "Duplicate transaction_id values were found."
        )

    # Validate dates
    parsed_dates = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    invalid_dates = parsed_dates.isna()

    if invalid_dates.any():
        errors.append(
            f"{invalid_dates.sum()} transaction(s) "
            "contain invalid dates."
        )

    df["date"] = parsed_dates

    # Validate amounts
    numeric_amounts = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    invalid_amounts = numeric_amounts.isna()

    if invalid_amounts.any():
        errors.append(
            f"{invalid_amounts.sum()} transaction(s) "
            "contain invalid amounts."
        )

    negative_amounts = numeric_amounts < 0

    if negative_amounts.any():
        errors.append(
            f"{negative_amounts.sum()} transaction(s) "
            "contain negative amounts."
        )

    df["amount"] = numeric_amounts

    # Validate text fields
    for column in [
        "description",
        "payee",
        "channel",
    ]:
        missing_values = df[column].isna()

        if missing_values.any():
            errors.append(
                f"{missing_values.sum()} transaction(s) "
                f"have missing {column} values."
            )

    # Stop if validation failed
    if errors:
        return {
            "success": False,
            "transactions": [],
            "errors": errors
        }

    # Convert dates to standard format
    df["date"] = df["date"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Convert to dictionaries
    transactions = df.to_dict(
        orient="records"
    )

    return {
        "success": True,
        "transactions": transactions,
        "errors": []
    }