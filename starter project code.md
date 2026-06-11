## Utility Functions
- `generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame`
  - Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.
- `init_database(db_engine: Engine, seed: int = 137) -> Engine`
  - Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels
- `create_transaction(item_name: str, transaction_type: str, quantity: int, price: float, date: Union[str, datetime],) -> int`
  - This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.
- `get_all_inventory(as_of_date: str) -> Dict[str, int]`
  - Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.
- `get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame`
  - Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.
- `get_supplier_delivery_date(input_date_str: str, quantity: int) -> str`
  - Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
      - ≤10 units: same day
      - 11–100 units: 1 day
      - 101–1000 units: 4 days
      - \>1000 units: 7 days
- `get_cash_balance(as_of_date: Union[str, datetime]) -> float`
  - Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

- `generate_financial_report(as_of_date: Union[str, datetime]) -> Dict`
  - Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

- `search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]`
  - Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.