# Business processes

How your key processes run end to end, in plain business language.

## Quote to cash

From a qualified opportunity to a paid invoice, with pricing and margin correct
at every step.

=== "Narrative"

    1. A salesperson builds a quotation from the customer's opportunity.
    2. Channel pricing is applied automatically: suggested retail price cascades
       through distributor discounts, co-terms, and fees, and the margin is
       shown on the order.
    3. The manager approves on margin.
    4. The order is confirmed and the customer invoice is issued with correct
       branding, bank, and tax details.
    5. Payment is tracked against the invoice.

=== "Diagram"

    ```mermaid
    flowchart LR
        Opp["Opportunity"] --> Quote["Quotation + pricing"]
        Quote --> Approve["Margin approval"]
        Approve --> Invoice["Customer invoice"]
        Invoice --> Paid["Payment tracked"]
    ```

## Invoice to purchase order

Procurement is generated from confirmed sales, with no manual re-keying.

=== "Narrative"

    1. A customer invoice is posted.
    2. The matching vendor purchase order is created and confirmed
       automatically, with the correct distributor cost applied.
    3. The buyer selects the fulfilling vendor, from your default vendors or the
       full list.
    4. Procurement proceeds against a clean, ready order.

=== "Diagram"

    ```mermaid
    flowchart LR
        Invoice["Customer invoice posted"] --> PO["Vendor PO created + confirmed"]
        PO --> Vendor["Vendor selected"]
        Vendor --> Fulfil["Procurement proceeds"]
    ```

More processes are documented here as they are configured and released.
