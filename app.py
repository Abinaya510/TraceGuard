from pathlib import Path
import json
import os
import csv
import io
from datetime import datetime

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"

STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="TraceGuard",
    description="Transaction Risk Investigation Assistant",
    version="1.0"
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    index_file = TEMPLATES_DIR / "index.html"

    if not index_file.exists():

        return HTMLResponse(
            """
            <html>
                <body>
                    <h1>TraceGuard</h1>
                    <p>ERROR: templates/index.html was not found.</p>
                </body>
            </html>
            """,
            status_code=500
        )

    html = index_file.read_text(
        encoding="utf-8"
    )

    return HTMLResponse(
        content=html,
        status_code=200
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_amount(value):

    if value is None:
        return 0.0

    text = str(value).strip()

    text = (
        text
        .replace("₹", "")
        .replace(",", "")
        .replace("$", "")
        .strip()
    )

    try:
        return float(text)

    except (ValueError, TypeError):

        return 0.0


def get_value(row, *names):

    for name in names:

        if name in row:

            value = row[name]

            if value is not None:

                return value

    return ""


def normalize_transaction(row, index):

    transaction_id = get_value(
        row,
        "transaction_id",
        "Transaction ID",
        "transaction id",
        "id",
        "ID"
    )

    if not transaction_id:

        transaction_id = f"TX{index:03d}"


    date = get_value(
        row,
        "date",
        "Date",
        "timestamp",
        "Timestamp",
        "datetime"
    )


    description = get_value(
        row,
        "description",
        "Description"
    )


    payee = get_value(
        row,
        "payee",
        "Payee",
        "merchant",
        "Merchant"
    )


    amount = parse_amount(
        get_value(
            row,
            "amount",
            "Amount"
        )
    )


    channel = get_value(
        row,
        "channel",
        "Channel"
    )


    return {

        "transaction_id":
            str(transaction_id),

        "date":
            str(date),

        "description":
            str(description),

        "payee":
            str(payee),

        "amount":
            amount,

        "channel":
            str(channel)
    }


def parse_csv(content):

    text = content.decode(
        "utf-8-sig",
        errors="replace"
    )

    reader = csv.DictReader(
        io.StringIO(text)
    )

    transactions = []

    for index, row in enumerate(
        reader,
        start=1
    ):

        transactions.append(
            normalize_transaction(
                row,
                index
            )
        )

    return transactions


# ============================================================
# RISK ANALYSIS
# ============================================================

def analyze_transactions(transactions):

    if not transactions:

        return {

            "success": False,

            "errors": [
                "No transactions found in the uploaded CSV."
            ]
        }


    # --------------------------------------------------------
    # Calculate typical transaction amount
    # --------------------------------------------------------

    amounts = [

        tx["amount"]

        for tx in transactions

        if tx["amount"] > 0
    ]


    if amounts:

        typical_amount = (
            sum(amounts)
            / len(amounts)
        )

    else:

        typical_amount = 0


    # --------------------------------------------------------
    # Flagged transactions
    # --------------------------------------------------------

    flagged_ids = set()

    signals = []


    # ========================================================
    # RULE 1: LARGE TRANSFER
    # ========================================================

    large_threshold = max(
        typical_amount * 10,
        50000
    )


    for tx in transactions:

        if tx["amount"] >= large_threshold:

            transaction_id = (
                tx["transaction_id"]
            )

            flagged_ids.add(
                transaction_id
            )


            signals.append({

                "rule":
                    "LARGE_TRANSFER",

                "severity":
                    "HIGH",

                "transaction_ids": [
                    transaction_id
                ],

                "explanation":
                    (
                        f"Transaction amount "
                        f"₹{tx['amount']:,.2f} "
                        f"is unusually large compared "
                        f"with the customer's typical "
                        f"spending amount of approximately "
                        f"₹{typical_amount:,.2f}."
                    )
            })


    # ========================================================
    # RULE 2: NEW PAYEE BURST
    # ========================================================

    parsed_transactions = []


    for tx in transactions:

        try:

            dt = datetime.strptime(
                tx["date"],
                "%Y-%m-%d %H:%M:%S"
            )

            parsed_transactions.append(
                (
                    dt,
                    tx
                )
            )

        except Exception:

            continue


    parsed_transactions.sort(
        key=lambda x: x[0]
    )


    payee_groups = {}


    for dt, tx in parsed_transactions:

        payee = tx["payee"]

        if not payee:

            continue


        if payee not in payee_groups:

            payee_groups[payee] = []


        payee_groups[payee].append(
            (
                dt,
                tx
            )
        )


    for payee, items in payee_groups.items():

        found_burst = False


        for i in range(
            len(items)
        ):

            start_time = items[i][0]

            window = []


            for j in range(
                i,
                len(items)
            ):

                difference = (
                    items[j][0]
                    - start_time
                ).total_seconds()


                if difference <= 3600:

                    window.append(
                        items[j]
                    )

                else:

                    break


            if len(window) >= 3:

                ids = [

                    item[1]["transaction_id"]

                    for item in window
                ]


                for transaction_id in ids:

                    flagged_ids.add(
                        transaction_id
                    )


                signals.append({

                    "rule":
                        "NEW_PAYEE_BURST",

                    "severity":
                        "HIGH",

                    "transaction_ids":
                        ids,

                    "explanation":
                        (
                            f"3 or more transactions "
                            f"were made to the previously "
                            f"unseen payee '{payee}' "
                            f"within 60 minutes."
                        )
                })


                found_burst = True

                break


        if found_burst:

            continue


    # ========================================================
    # RULE 3: ODD HOUR
    # ========================================================

    for tx in transactions:

        try:

            dt = datetime.strptime(
                tx["date"],
                "%Y-%m-%d %H:%M:%S"
            )


            if 0 <= dt.hour <= 5:

                transaction_id = (
                    tx["transaction_id"]
                )


                flagged_ids.add(
                    transaction_id
                )


                signals.append({

                    "rule":
                        "ODD_HOUR",

                    "severity":
                        "MEDIUM",

                    "transaction_ids": [
                        transaction_id
                    ],

                    "explanation":
                        (
                            f"Transaction occurred at "
                            f"{dt.strftime('%H:%M')}, "
                            f"within the defined unusual "
                            f"activity window "
                            f"(00:00–05:59)."
                        )
                })


        except Exception:

            continue


    # ========================================================
    # RULE 4: PATTERN DEVIATION
    # ========================================================

    if typical_amount > 0:

        for tx in transactions:

            if tx["amount"] > (
                typical_amount * 10
            ):

                transaction_id = (
                    tx["transaction_id"]
                )


                flagged_ids.add(
                    transaction_id
                )


                signals.append({

                    "rule":
                        "PATTERN_DEVIATION",

                    "severity":
                        "MEDIUM",

                    "transaction_ids": [
                        transaction_id
                    ],

                    "explanation":
                        (
                            f"Transaction differs "
                            f"substantially from the "
                            f"customer's established "
                            f"spending pattern: "
                            f"₹{tx['amount']:,.2f} is more "
                            f"than 10× the typical "
                            f"spending amount of "
                            f"approximately "
                            f"₹{typical_amount:,.2f}."
                        )
                })


    # ========================================================
    # RISK SCORE
    # ========================================================

    has_high = any(

        signal["severity"] == "HIGH"

        for signal in signals
    )


    has_medium = any(

        signal["severity"] == "MEDIUM"

        for signal in signals
    )


    if has_high and has_medium:

        risk_score = 100

    elif has_high:

        risk_score = 80

    elif has_medium:

        risk_score = 60

    else:

        risk_score = 0


    attention_required = (
        len(flagged_ids) > 0
    )


    # ========================================================
    # FLAGGED TRANSACTIONS
    # ========================================================

    flagged_transactions = [

        tx

        for tx in transactions

        if tx["transaction_id"]
        in flagged_ids
    ]


    # ========================================================
    # EVIDENCE
    # ========================================================

    evidence = []


    for signal in signals:

        matching_transactions = [

            tx

            for tx in transactions

            if tx["transaction_id"]
            in signal["transaction_ids"]
        ]


        evidence.append({

            "rule":
                signal["rule"],

            "severity":
                signal["severity"],

            "explanation":
                signal["explanation"],

            "transactions":
                matching_transactions
        })


    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "success":
            True,

        "transaction_count":
            len(transactions),

        "attention_required":
            attention_required,

        "risk_score":
            risk_score,

        "flagged_transaction_ids":
            list(flagged_ids),

        "flagged_transactions":
            flagged_transactions,

        "signals":
            signals,

        "evidence":
            evidence
    }


# ============================================================
# OPTIONAL GEMINI REPORT
# ============================================================

def generate_gemini_report(result):

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    # --------------------------------------------------------
    # Gemini is optional.
    # --------------------------------------------------------

    if not api_key:

        return {

            "investigation_report":
                None,

            "gemini_success":
                False,

            "gemini_error":
                "Gemini API key is not configured."
        }


    try:

        from google import genai


        client = genai.Client(
            api_key=api_key
        )


        prompt = f"""
You are a banking transaction investigation assistant.

Analyze the following transaction-risk result.

Create a concise investigation report containing:

1. Overall risk assessment
2. Suspicious transaction pattern
3. Most important transactions
4. Risk signals
5. Recommended investigator actions

Do not state that fraud is proven.
Use cautious language such as suspicious,
unusual, or requires investigation.

Transaction analysis:

{json.dumps(result, indent=2, ensure_ascii=False)}
"""


        response = client.models.generate_content(

            model="gemini-3-flash-preview",

            contents=prompt
        )


        report = getattr(
            response,
            "text",
            None
        )


        if not report:

            raise Exception(
                "Gemini returned an empty response."
            )


        return {

            "investigation_report":
                report,

            "gemini_success":
                True,

            "gemini_error":
                None
        }


    except Exception as exc:

        print(
            "Gemini unavailable:",
            repr(exc)
        )


        return {

            "investigation_report":
                None,

            "gemini_success":
                False,

            "gemini_error":
                str(exc)
        }


# ============================================================
# ANALYZE ENDPOINT
# ============================================================

@app.post("/api/analyze")
async def analyze_api(
    file: UploadFile = File(...)
):

    try:

        # ----------------------------------------------------
        # Read uploaded file
        # ----------------------------------------------------

        content = await file.read()


        if not content:

            return JSONResponse(

                status_code=400,

                content={

                    "success":
                        False,

                    "errors": [
                        "Uploaded file is empty."
                    ]
                }
            )


        # ----------------------------------------------------
        # Parse CSV
        # ----------------------------------------------------

        transactions = parse_csv(
            content
        )


        # ----------------------------------------------------
        # Run risk engine
        # ----------------------------------------------------

        result = analyze_transactions(
            transactions
        )


        if not result.get(
            "success",
            False
        ):

            return JSONResponse(

                status_code=400,

                content=result
            )


        # ----------------------------------------------------
        # Try Gemini
        # ----------------------------------------------------

        gemini_result = (
            generate_gemini_report(
                result
            )
        )


        result.update(
            gemini_result
        )


        # ----------------------------------------------------
        # ALWAYS return successful analysis
        # even if Gemini fails.
        # ----------------------------------------------------

        return JSONResponse(

            status_code=200,

            content=result
        )


    except Exception as exc:

        print(
            "ANALYSIS ERROR:",
            repr(exc)
        )


        return JSONResponse(

            status_code=500,

            content={

                "success":
                    False,

                "errors": [
                    f"Analysis failed: {exc}"
                ]
            }
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    import uvicorn


    print()
    print("==============================")
    print("TRACEGUARD")
    print("==============================")
    print()


    uvicorn.run(

        app,

        host="0.0.0.0",

        port=8000
    )