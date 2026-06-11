# Munder Difflin Multi-Agent Reflection

## Workflow Diagram Explanation

The implemented workflow is Orchestrator -> Inventory Worker -> Quoting Worker -> Sales Worker -> customer response. The orchestrator parses each customer request, resolves requested products to catalog items, and delegates availability checks to the inventory agent. If every item can be supplied by the requested delivery date, the orchestrator asks the quoting agent to calculate a customer-safe quote using catalog prices, historical quote context, and volume discounts. Approved quotes are then delegated to the sales agent, which records any required supplier stock transactions and the customer sale transactions. If a worker reports an unsupported item, missed supplier deadline, or insufficient operating cash, the orchestrator stops the workflow and returns an explainable non-fulfillment response.

## Evaluation Results

The evaluation used all 20 rows from `quote_requests_sample.csv` and wrote the detailed results to `test_results.csv`. 9 requests were fulfilled, 11 requests were not fulfilled, and 9 requests changed the cash balance. Strengths of the system include clear separation of agent responsibilities, deterministic reproducibility for the sample dataset, explicit delivery-date reasoning, and customer responses that include requested items, pricing, discount rationale, and non-fulfillment reasons without exposing internal cash balances or margins.

Representative non-fulfillment reasons: 200 balloons for the parade: balloons are outside the paper supply catalog; 5,000 sheets of A3 paper: plain A3 paper is not available in the current catalog; A4 paper: supplier replenishment would arrive 2025-04-11, after the requested 2025-04-10 delivery date

## Further Improvements

1. Add a stronger natural-language parser or LLM extraction step for more ambiguous product names, sizes, and units such as reams versus sheets.
2. Persist formal quote records in a dedicated quotes table after each successful quote so future evaluations can learn from newly generated pricing.
3. Add policy controls for partial fulfillment, substitutions, and customer approval before replacing an unavailable exact product with a close stocked catalog item.
