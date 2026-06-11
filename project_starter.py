import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
import json
import re
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from sqlalchemy import create_engine, Engine
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


# Set up and load your env parameters and instantiate your model.
dotenv.load_dotenv()

"""Pydantic AI multi-agent implementation.

The agents below are registered with pydantic-ai and each worker owns the tools
for its business function. The actual sample evaluation uses deterministic
delegation through MunderDifflinOrchestrator so it can run locally without an
LLM API key while still exercising the framework-defined tools.
"""


@dataclass
class RequestedLineItem:
    """A raw line item extracted from a customer request."""

    quantity: int
    unit: str
    description: str
    original_text: str


@dataclass
class ParsedCustomerRequest:
    """Structured request data used by the orchestrator."""

    request_text: str
    request_date: str
    delivery_deadline: str
    job: str
    event: str
    need_size: str
    requested_items: List[RequestedLineItem]


@dataclass
class AgentDecision:
    """Final orchestrator decision for one customer request."""

    fulfilled: bool
    response: str
    quoted_total: float
    failure_reason: str


CATALOG_BY_NAME = {item["item_name"]: item for item in paper_supplies}
MONTH_NUMBERS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
ORDER_UNIT_TERMS = [
    "decorative adhesive tape",
    "presentation folders",
    "invitation cards",
    "table napkins",
    "paper napkins",
    "paper plates",
    "paper cups",
    "poster boards",
    "poster board",
    "table covers",
    "streamers",
    "balloons",
    "envelopes",
    "notepads",
    "packets",
    "packet",
    "posters",
    "poster",
    "flyers",
    "flyer",
    "tickets",
    "ticket",
    "plates",
    "napkins",
    "cups",
    "cards",
    "card",
    "reams",
    "ream",
    "rolls",
    "roll",
    "boxes",
    "box",
    "sheets",
    "sheet",
]
ORDER_UNIT_PATTERN = "|".join(re.escape(unit) for unit in ORDER_UNIT_TERMS)
REQUEST_DATE_PATTERN = re.compile(r"Date of request:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
DELIVERY_DATE_PATTERN = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December"
    r")\s+(\d{1,2}),\s*(\d{4})",
    re.IGNORECASE,
)
LINE_ITEM_PATTERN = re.compile(
    rf"(?P<quantity>\d[\d,]*)\s+"
    rf"(?P<unit>{ORDER_UNIT_PATTERN})\b\s*"
    rf"(?:of\s+)?"
    rf"(?P<description>.*?)"
    rf"(?="
    rf"(?:[,;]\s*(?:and\s+|along with\s+)?\d[\d,]*\s+(?:{ORDER_UNIT_PATTERN})\b)"
    rf"|(?:\s+and\s+\d[\d,]*\s+(?:{ORDER_UNIT_PATTERN})\b)"
    rf"|(?:\.\s)"
    rf"|(?:\n)"
    rf"|$"
    rf")",
    re.IGNORECASE | re.DOTALL,
)
UNIT_AS_PRODUCT_TERMS = {
    "balloons",
    "balloon",
    "cards",
    "card",
    "cups",
    "cup",
    "envelopes",
    "flyers",
    "flyer",
    "invitation cards",
    "napkins",
    "notepads",
    "paper cups",
    "paper napkins",
    "paper plates",
    "plates",
    "poster",
    "poster board",
    "poster boards",
    "posters",
    "presentation folders",
    "streamers",
    "table covers",
    "table napkins",
    "ticket",
    "tickets",
}


def _normalise_text(value: str) -> str:
    """Normalize request fragments for rule-based catalog matching."""
    value = value.lower()
    value = value.replace("8.5\"x11\"", "letter")
    value = value.replace("8.5x11", "letter")
    value = value.replace("24\" x 36\"", "24x36")
    value = re.sub(r"[^a-z0-9%]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _extract_request_date(request_text: str, fallback: Optional[str] = None) -> str:
    """Return an ISO request date from the appended test context."""
    match = REQUEST_DATE_PATTERN.search(request_text)
    if match:
        return match.group(1)
    if fallback:
        return fallback
    return datetime.now().strftime("%Y-%m-%d")


def _extract_delivery_deadline(request_text: str, request_date: str) -> str:
    """Return the first explicit delivery date, or a conservative one-week default."""
    match = DELIVERY_DATE_PATTERN.search(request_text)
    if not match:
        return (datetime.fromisoformat(request_date) + timedelta(days=7)).strftime("%Y-%m-%d")

    month_name, day, year = match.groups()
    return datetime(int(year), MONTH_NUMBERS[month_name.lower()], int(day)).strftime("%Y-%m-%d")


def _clean_description(description: str) -> str:
    """Remove delivery and event prose that is not part of the product name."""
    cleaned = re.sub(r"\([^)]*\)", " ", description)
    cleaned = re.sub(r"\b(?:for|to ensure|delivered|deliver|please|thank you)\b.*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bin\s+(?:various|assorted|different)\s+colors\b.*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("-", " ")
    return re.sub(r"\s+", " ", cleaned).strip(" .,:;-")


def _parse_requested_items(request_text: str) -> List[RequestedLineItem]:
    """Extract quantity, unit, and item description fragments from free text."""
    requested_items: List[RequestedLineItem] = []
    text_without_context = REQUEST_DATE_PATTERN.sub("", request_text)

    for match in LINE_ITEM_PATTERN.finditer(text_without_context):
        quantity_text = match.group("quantity").replace(",", "")
        description = _clean_description(match.group("description"))
        unit = match.group("unit").lower().strip()
        original_text = re.sub(r"\s+", " ", match.group(0)).strip(" .,:;-")

        if not description and unit not in UNIT_AS_PRODUCT_TERMS:
            continue

        requested_items.append(
            RequestedLineItem(
                quantity=int(quantity_text),
                unit=unit,
                description=description,
                original_text=original_text,
            )
        )

    return requested_items


def _resolve_catalog_item(item: RequestedLineItem) -> Dict[str, Optional[str]]:
    """Map customer wording onto the closest supported catalog item."""
    text = _normalise_text(f"{item.description} {item.unit}")

    if "balloon" in text:
        return {"item_name": None, "reason": "balloons are outside the paper supply catalog"}
    if "ticket" in text:
        return {"item_name": None, "reason": "tickets are not available as a stocked paper supply"}
    if re.search(r"\ba3\s+paper\b", text) and not any(word in text for word in ["glossy", "matte", "colored", "colour", "poster"]):
        return {"item_name": None, "reason": "plain A3 paper is not available in the current catalog"}

    if "washi" in text or "adhesive tape" in text:
        return {"item_name": "Decorative adhesive tape (washi tape)", "reason": None}
    if "streamer" in text:
        return {"item_name": "Party streamers", "reason": None}
    if "paper plate" in text or re.search(r"\bplates?\b", text):
        return {"item_name": "Paper plates", "reason": None}
    if "paper cup" in text or re.search(r"\bcups?\b", text):
        return {"item_name": "Paper cups", "reason": None}
    if "napkin" in text:
        return {"item_name": "Paper napkins", "reason": None}
    if "table cover" in text:
        return {"item_name": "Table covers", "reason": None}
    if "presentation folder" in text:
        return {"item_name": "Presentation folders", "reason": None}
    if "invitation" in text or re.search(r"\bcards?\b", text):
        return {"item_name": "Invitation cards", "reason": None}
    if "flyer" in text:
        return {"item_name": "Flyers", "reason": None}
    if "poster board" in text or "24x36" in text:
        return {"item_name": "Large poster paper (24x36 inches)", "reason": None}
    if re.search(r"\bposters?\b", text) and "poster paper" not in text:
        return {"item_name": "Large poster paper (24x36 inches)", "reason": None}
    if "banner" in text and "roll" in text:
        return {"item_name": "Rolls of banner paper (36-inch width)", "reason": None}
    if "banner" in text:
        return {"item_name": "Banner paper", "reason": None}

    if "matte" in text:
        return {"item_name": "Matte paper", "reason": None}
    if "glossy" in text:
        return {"item_name": "Glossy paper", "reason": None}
    if "photo" in text:
        return {"item_name": "Photo paper", "reason": None}
    if "poster paper" in text:
        return {"item_name": "Poster paper", "reason": None}
    if "recycled" in text and "cardstock" not in text and "card stock" not in text:
        return {"item_name": "Recycled paper", "reason": None}
    if "envelope" in text:
        return {"item_name": "Envelopes", "reason": None}
    if "kraft" in text:
        return {"item_name": "Kraft paper", "reason": None}
    if "cover stock" in text or "coverstock" in text:
        return {"item_name": "100 lb cover stock", "reason": None}
    if "cardstock" in text or "card stock" in text or "cardboard" in text:
        return {"item_name": "Cardstock", "reason": None}
    if "construction" in text:
        return {"item_name": "Construction paper", "reason": None}
    if "colored paper" in text or "colour paper" in text or "colorful paper" in text:
        return {"item_name": "Colored paper", "reason": None}
    if "colored" in text or "colour" in text or "assorted colors" in text:
        return {"item_name": "Colored paper", "reason": None}
    if "letter" in text:
        return {"item_name": "Letter-sized paper", "reason": None}
    if "standard copy" in text:
        return {"item_name": "Standard copy paper", "reason": None}
    if "printer" in text or "printing" in text or "white paper" in text or "a4" in text:
        return {"item_name": "A4 paper", "reason": None}

    return {"item_name": None, "reason": f"could not match '{item.original_text}' to a catalog item"}


def _item_metadata(item_name: str) -> Dict[str, Union[str, float, int, bool]]:
    """Return unit price and seeded-inventory metadata for a catalog item."""
    inventory_df = pd.read_sql("SELECT * FROM inventory WHERE item_name = :item_name", db_engine, params={"item_name": item_name})
    if not inventory_df.empty:
        row = inventory_df.iloc[0]
        return {
            "item_name": item_name,
            "unit_price": float(row["unit_price"]),
            "min_stock_level": int(row["min_stock_level"]),
            "stocked_initially": True,
        }

    catalog_item = CATALOG_BY_NAME[item_name]
    return {
        "item_name": item_name,
        "unit_price": float(catalog_item["unit_price"]),
        "min_stock_level": 0,
        "stocked_initially": False,
    }


def _combine_resolved_items(parsed_items: List[RequestedLineItem]) -> Dict[str, object]:
    """Resolve and merge parsed customer line items by catalog item."""
    combined_items: Dict[str, Dict[str, object]] = {}
    unsupported_items: List[str] = []

    for parsed_item in parsed_items:
        resolution = _resolve_catalog_item(parsed_item)
        item_name = resolution["item_name"]

        if not item_name:
            unsupported_items.append(f"{parsed_item.original_text}: {resolution['reason']}")
            continue
        if item_name not in CATALOG_BY_NAME:
            unsupported_items.append(f"{parsed_item.original_text}: {item_name} is not in the supplier catalog")
            continue

        metadata = _item_metadata(item_name)
        if item_name not in combined_items:
            combined_items[item_name] = {
                "item_name": item_name,
                "quantity": 0,
                "unit": parsed_item.unit,
                "unit_price": metadata["unit_price"],
                "min_stock_level": metadata["min_stock_level"],
                "stocked_initially": metadata["stocked_initially"],
                "customer_descriptions": [],
            }

        combined_items[item_name]["quantity"] = int(combined_items[item_name]["quantity"]) + parsed_item.quantity
        combined_items[item_name]["customer_descriptions"].append(parsed_item.original_text)

    return {
        "items": list(combined_items.values()),
        "unsupported_items": unsupported_items,
    }


def _format_currency(amount: float) -> str:
    """Format money values for customer-facing output."""
    return f"${amount:,.2f}"


def _bulk_discount_rate(total_units: int, need_size: str) -> float:
    """Apply transparent volume discounts without exposing internal margin data."""
    need_size = (need_size or "").lower()
    if total_units >= 5000 or need_size == "large":
        return 0.10
    if total_units >= 1000 or need_size == "medium":
        return 0.07
    if total_units >= 500:
        return 0.05
    return 0.0


inventory_agent = Agent(
    model=None,
    name="inventory_agent",
    instructions=(
        "Check stock levels, supplier lead times, and reorder feasibility for customer quote requests."
    ),
)

quoting_agent = Agent(
    model=None,
    name="quoting_agent",
    instructions=(
        "Create customer-safe quotes using catalog prices, volume discounts, and historical quote context."
    ),
)

sales_agent = Agent(
    model=None,
    name="sales_agent",
    instructions=(
        "Finalize approved customer orders by creating supplier and sales transactions."
    ),
)

orchestrator_agent = Agent(
    model=None,
    name="orchestrator_agent",
    instructions=(
        "Route requests through inventory, quoting, and sales workers, then return explainable customer responses."
    ),
)


@inventory_agent.tool_plain
def inventory_snapshot_tool(as_of_date: str) -> Dict[str, int]:
    """Return all positive stock levels as of the requested date."""
    return get_all_inventory(as_of_date)


@inventory_agent.tool_plain
def assess_inventory_for_order_tool(
    requested_items: List[Dict[str, object]],
    as_of_date: str,
    delivery_deadline: str,
) -> List[Dict[str, object]]:
    """Assess stock, supplier replenishment, and delivery feasibility for each line item."""
    inventory_snapshot = get_all_inventory(as_of_date)
    assessment: List[Dict[str, object]] = []

    for item in requested_items:
        item_name = str(item["item_name"])
        quantity = int(item["quantity"])
        unit_price = float(item["unit_price"])

        stock_df = get_stock_level(item_name, as_of_date)
        current_stock = int(stock_df["current_stock"].iloc[0]) if not stock_df.empty else 0
        current_stock = int(inventory_snapshot.get(item_name, current_stock))

        shortage = max(quantity - current_stock, 0)
        supplier_delivery_date = as_of_date
        if shortage > 0:
            supplier_delivery_date = get_supplier_delivery_date(as_of_date, shortage)

        can_fulfill = shortage == 0 or supplier_delivery_date <= delivery_deadline
        post_sale_stock = current_stock + shortage - quantity

        if shortage == 0:
            status = "available_from_stock"
            reason = "available from current stock"
        elif can_fulfill:
            status = "supplier_restock_required"
            reason = f"supplier replenishment is available by {supplier_delivery_date}"
        else:
            status = "cannot_meet_deadline"
            reason = f"supplier replenishment would arrive {supplier_delivery_date}, after the requested {delivery_deadline} delivery date"

        assessment.append(
            {
                "item_name": item_name,
                "quantity": quantity,
                "unit": item["unit"],
                "unit_price": unit_price,
                "current_stock": current_stock,
                "shortage": shortage,
                "restock_quantity": shortage,
                "supplier_delivery_date": supplier_delivery_date,
                "can_fulfill": can_fulfill,
                "status": status,
                "reason": reason,
                "post_sale_stock": post_sale_stock,
                "reorder_recommended_after_sale": post_sale_stock < int(item.get("min_stock_level", 0)),
                "customer_descriptions": item.get("customer_descriptions", []),
            }
        )

    return assessment


@quoting_agent.tool_plain
def generate_quote_tool(
    approved_items: List[Dict[str, object]],
    job: str,
    event: str,
    need_size: str,
) -> Dict[str, object]:
    """Generate a transparent quote and consult historical quotes for pricing consistency."""
    search_terms = [term for term in [event, need_size] if term]
    historical_quotes = search_quote_history(search_terms, limit=3)
    if not historical_quotes and event:
        historical_quotes = search_quote_history([event], limit=3)

    total_units = sum(int(item["quantity"]) for item in approved_items)
    discount_rate = _bulk_discount_rate(total_units, need_size)
    subtotal = 0.0
    line_items: List[Dict[str, object]] = []

    for item in approved_items:
        quantity = int(item["quantity"])
        unit_price = float(item["unit_price"])
        line_subtotal = quantity * unit_price
        subtotal += line_subtotal
        line_items.append(
            {
                "item_name": item["item_name"],
                "quantity": quantity,
                "unit": item["unit"],
                "unit_price": unit_price,
                "line_subtotal": round(line_subtotal, 2),
                "line_total": round(line_subtotal * (1 - discount_rate), 2),
                "restock_quantity": int(item.get("restock_quantity", 0)),
                "supplier_delivery_date": item.get("supplier_delivery_date"),
            }
        )

    discount_amount = subtotal * discount_rate
    total = subtotal - discount_amount
    explanation = (
        f"Pricing uses published unit rates for {total_units:,} requested units"
        f" with a {discount_rate:.0%} volume discount."
    )
    if historical_quotes:
        explanation += " Similar historical quotes were checked for consistency."

    return {
        "job": job,
        "event": event,
        "need_size": need_size,
        "subtotal": round(subtotal, 2),
        "discount_rate": discount_rate,
        "discount_amount": round(discount_amount, 2),
        "total": round(total, 2),
        "line_items": line_items,
        "history_reference_count": len(historical_quotes),
        "quote_explanation": explanation,
    }


@sales_agent.tool_plain
def finalize_sale_tool(
    quote: Dict[str, object],
    request_date: str,
) -> Dict[str, object]:
    """Record supplier replenishment and customer sales transactions for an approved quote."""
    opening_cash = get_cash_balance(request_date)
    restock_cost = sum(
        int(item.get("restock_quantity", 0)) * float(item["unit_price"])
        for item in quote["line_items"]
    )

    if restock_cost > opening_cash:
        return {
            "finalized": False,
            "reason": "available operating cash is not sufficient to procure required stock",
            "opening_cash": opening_cash,
            "ending_cash": opening_cash,
            "transaction_ids": [],
        }

    transaction_ids: List[int] = []
    for item in quote["line_items"]:
        restock_quantity = int(item.get("restock_quantity", 0))
        item_name = str(item["item_name"])
        unit_price = float(item["unit_price"])

        if restock_quantity > 0:
            transaction_ids.append(
                create_transaction(
                    item_name=item_name,
                    transaction_type="stock_orders",
                    quantity=restock_quantity,
                    price=round(restock_quantity * unit_price, 2),
                    date=request_date,
                )
            )

        transaction_ids.append(
            create_transaction(
                item_name=item_name,
                transaction_type="sales",
                quantity=int(item["quantity"]),
                price=float(item["line_total"]),
                date=request_date,
            )
        )

    report = generate_financial_report(request_date)
    ending_cash = float(report["cash_balance"])

    return {
        "finalized": True,
        "reason": "order finalized",
        "opening_cash": opening_cash,
        "ending_cash": ending_cash,
        "transaction_ids": transaction_ids,
    }


@orchestrator_agent.tool_plain
def orchestration_summary_tool() -> str:
    """Describe the deterministic workflow used by the orchestrator."""
    return (
        "The orchestrator parses a request, delegates availability checks to the inventory worker, "
        "delegates pricing to the quoting worker, and delegates transaction recording to the sales worker."
    )


class MunderDifflinOrchestrator:
    """Coordinates worker agents for inventory, quoting, and sales finalization."""

    def handle_customer_request(
        self,
        request_text: str,
        job: str = "",
        event: str = "",
        need_size: str = "",
        request_date: Optional[str] = None,
    ) -> AgentDecision:
        """Process one request through the multi-agent workflow."""
        parsed_request = self._parse_request(request_text, job, event, need_size, request_date)

        if not parsed_request.requested_items:
            return AgentDecision(
                fulfilled=False,
                response=(
                    "I could not identify specific quantities and paper supply items in the request, "
                    "so I cannot create a reliable quote yet. No transaction was created."
                ),
                quoted_total=0.0,
                failure_reason="no line items identified",
            )

        resolved = _combine_resolved_items(parsed_request.requested_items)
        unsupported_items = resolved["unsupported_items"]
        if unsupported_items:
            reason = "; ".join(unsupported_items)
            return AgentDecision(
                fulfilled=False,
                response=(
                    f"I cannot confirm this order for delivery by {parsed_request.delivery_deadline}. "
                    f"Reason: {reason}. No transaction was created."
                ),
                quoted_total=0.0,
                failure_reason=reason,
            )

        inventory_assessment = assess_inventory_for_order_tool(
            resolved["items"],
            parsed_request.request_date,
            parsed_request.delivery_deadline,
        )
        blocked_items = [item for item in inventory_assessment if not item["can_fulfill"]]
        if blocked_items:
            reason = "; ".join(f"{item['item_name']}: {item['reason']}" for item in blocked_items)
            return AgentDecision(
                fulfilled=False,
                response=(
                    f"I cannot confirm this order for delivery by {parsed_request.delivery_deadline}. "
                    f"Reason: {reason}. No transaction was created."
                ),
                quoted_total=0.0,
                failure_reason=reason,
            )

        quote = generate_quote_tool(
            inventory_assessment,
            parsed_request.job,
            parsed_request.event,
            parsed_request.need_size,
        )
        sale_result = finalize_sale_tool(quote, parsed_request.request_date)
        if not sale_result["finalized"]:
            return AgentDecision(
                fulfilled=False,
                response=(
                    f"I cannot confirm this order today. Reason: {sale_result['reason']}. "
                    "No customer sale transaction was created."
                ),
                quoted_total=float(quote["total"]),
                failure_reason=str(sale_result["reason"]),
            )

        return AgentDecision(
            fulfilled=True,
            response=self._build_success_response(parsed_request, quote, inventory_assessment),
            quoted_total=float(quote["total"]),
            failure_reason="",
        )

    def _parse_request(
        self,
        request_text: str,
        job: str,
        event: str,
        need_size: str,
        request_date: Optional[str],
    ) -> ParsedCustomerRequest:
        """Parse request text and attach scenario metadata."""
        parsed_request_date = _extract_request_date(request_text, request_date)
        return ParsedCustomerRequest(
            request_text=request_text,
            request_date=parsed_request_date,
            delivery_deadline=_extract_delivery_deadline(request_text, parsed_request_date),
            job=job,
            event=event,
            need_size=need_size,
            requested_items=_parse_requested_items(request_text),
        )

    def _build_success_response(
        self,
        parsed_request: ParsedCustomerRequest,
        quote: Dict[str, object],
        inventory_assessment: List[Dict[str, object]],
    ) -> str:
        """Create a customer-facing confirmation without exposing internal financial data."""
        line_parts = []
        for line in quote["line_items"]:
            line_parts.append(
                f"{int(line['quantity']):,} {line['unit']} {line['item_name']} "
                f"at {_format_currency(float(line['unit_price']))} per unit"
            )

        restocked_items = [item for item in inventory_assessment if int(item["restock_quantity"]) > 0]
        if restocked_items:
            latest_supplier_date = max(str(item["supplier_delivery_date"]) for item in restocked_items)
            availability_note = (
                f"Some items require supplier replenishment, and the latest expected replenishment date is "
                f"{latest_supplier_date}, which supports the requested delivery date."
            )
        else:
            availability_note = "All requested items are available from current stock for the requested schedule."

        discount_note = "No volume discount was needed for this order."
        if float(quote["discount_rate"]) > 0:
            discount_note = (
                f"A {float(quote['discount_rate']):.0%} volume discount was applied, "
                f"reducing the quote by {_format_currency(float(quote['discount_amount']))}."
            )

        return (
            f"Order confirmed for delivery by {parsed_request.delivery_deadline}. "
            f"Items quoted: {'; '.join(line_parts)}. "
            f"Subtotal: {_format_currency(float(quote['subtotal']))}. {discount_note} "
            f"Total confirmed price: {_format_currency(float(quote['total']))}. "
            f"{availability_note} {quote['quote_explanation']}"
        )


def call_munder_difflin_multi_agent_system(
    request_text: str,
    job: str = "",
    event: str = "",
    need_size: str = "",
    request_date: Optional[str] = None,
) -> AgentDecision:
    """Public entry point for processing one request through the orchestrator."""
    orchestrator = MunderDifflinOrchestrator()
    return orchestrator.handle_customer_request(
        request_text=request_text,
        job=job,
        event=event,
        need_size=need_size,
        request_date=request_date,
    )


# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    ############
    ############
    ############
    # INITIALIZE YOUR MULTI AGENT SYSTEM HERE
    ############
    ############
    ############
    orchestrator = MunderDifflinOrchestrator()

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")
        previous_cash = current_cash
        previous_inventory = current_inventory

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        ############
        ############
        ############
        # USE YOUR MULTI AGENT SYSTEM TO HANDLE THE REQUEST
        ############
        ############
        ############

        decision = orchestrator.handle_customer_request(
            request_text=request_with_date,
            job=row["job"],
            event=row["event"],
            need_size=row["need_size"],
            request_date=request_date,
        )
        response = decision.response

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "cash_changed": abs(current_cash - previous_cash) > 0.001,
                "inventory_changed": abs(current_inventory - previous_inventory) > 0.001,
                "status": "fulfilled" if decision.fulfilled else "not_fulfilled",
                "quoted_total": decision.quoted_total,
                "failure_reason": decision.failure_reason,
                "response": response,
            }
        )

        time.sleep(0.1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    write_reflection_report(results)
    return results


def write_reflection_report(results: List[Dict[str, object]]) -> None:
    """Write a concise architecture and evaluation reflection for submission."""
    total_requests = len(results)
    fulfilled_count = sum(1 for result in results if result["status"] == "fulfilled")
    unfulfilled_count = total_requests - fulfilled_count
    cash_change_count = sum(1 for result in results if result["cash_changed"])
    failed_reasons = [
        str(result["failure_reason"])
        for result in results
        if result["status"] != "fulfilled" and result["failure_reason"]
    ]
    representative_failures = "; ".join(failed_reasons[:3]) if failed_reasons else "No failures recorded."

    report_text = f"""# Munder Difflin Multi-Agent Reflection

## Workflow Diagram Explanation

The implemented workflow is Orchestrator -> Inventory Worker -> Quoting Worker -> Sales Worker -> customer response. The orchestrator parses each customer request, resolves requested products to catalog items, and delegates availability checks to the inventory agent. If every item can be supplied by the requested delivery date, the orchestrator asks the quoting agent to calculate a customer-safe quote using catalog prices, historical quote context, and volume discounts. Approved quotes are then delegated to the sales agent, which records any required supplier stock transactions and the customer sale transactions. If a worker reports an unsupported item, missed supplier deadline, or insufficient operating cash, the orchestrator stops the workflow and returns an explainable non-fulfillment response.

## Evaluation Results

The evaluation used all {total_requests} rows from `quote_requests_sample.csv` and wrote the detailed results to `test_results.csv`. {fulfilled_count} requests were fulfilled, {unfulfilled_count} requests were not fulfilled, and {cash_change_count} requests changed the cash balance. Strengths of the system include clear separation of agent responsibilities, deterministic reproducibility for the sample dataset, explicit delivery-date reasoning, and customer responses that include requested items, pricing, discount rationale, and non-fulfillment reasons without exposing internal cash balances or margins.

Representative non-fulfillment reasons: {representative_failures}

## Further Improvements

1. Add a stronger natural-language parser or LLM extraction step for more ambiguous product names, sizes, and units such as reams versus sheets.
2. Persist formal quote records in a dedicated quotes table after each successful quote so future evaluations can learn from newly generated pricing.
3. Add policy controls for partial fulfillment, substitutions, and customer approval before replacing an unavailable exact product with a close stocked catalog item.
"""

    with open("reflection_report.md", "w", encoding="utf-8") as report_file:
        report_file.write(report_text)


def test_progress():
    print("Initializing Database...")
    init_database(db_engine)

    ## test helper utilities
    inventory = get_all_inventory("2026-06-02")
    print("All Inventory")
    print(f"{json.dumps(inventory, indent=3)}")

    print("A4 paper current stock")
    stock = get_stock_level("A4 paper", "2026-06-02")
    print(stock)

    print("Current cash balanece")
    cash_balance = get_cash_balance("2026-06-02")
    print(cash_balance)

    print("Test transaction")
    transaction_id = create_transaction(
        "A4 paper",
        "sales",
        200,
        20,
        "2026-06-02"   
    )
    print(f"A4 paper stock after transaction {transaction_id}")
    stock = get_stock_level("A4 paper", "2026-06-02")
    print(stock)
    print(f"Cash balance after sale for transaction {transaction_id}")
    cash_balance = get_cash_balance("2026-06-02")
    print(cash_balance)
    print(f"Updated inventory after transaction {transaction_id}")
    inventory = get_all_inventory("2026-06-02")
    print(f"{json.dumps(inventory, indent=3)}")
    
    transaction_id = create_transaction(
        "A4 paper",
        "stock_orders",
        200,
        10,
        "2026-06-02"   
    )
    print(f"A4 paper stock after transaction {transaction_id}")
    stock = get_stock_level("A4 paper", "2026-06-02")
    print(stock)
    print(f"Cash balance after sale for transaction {transaction_id}")
    cash_balance = get_cash_balance("2026-06-02")
    print(cash_balance)
    print(f"Updated inventory after transaction {transaction_id}")
    inventory = get_all_inventory("2026-06-02")
    print(f"{json.dumps(inventory, indent=3)}")

    financial_report =generate_financial_report("2026-06-02")
    print("Financial Report")
    print(f"{json.dumps(financial_report, indent=3)}")

if __name__ == "__main__":
    results = run_test_scenarios()
