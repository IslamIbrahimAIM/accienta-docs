---
search:
  exclude: true
---

# Architecture Decisions

Significant choices made during the implementation, with the reasoning behind
them. These are recorded so the solution stays understandable over time.

<!-- GENERATED:decisions -->
### Cost of revenue carries the customer discount; revenue measured gross

**Decision:** On sale.order.line the cost of revenue is the supplier payable plus the customer discount granted:

  vendor_net    = 1 - backend% - fee% - disti%
  payable_unit  = SRP2 x vendor_net
  gross_unit    = price_unit x (1 - disti%)
  discount_cost = gross_unit x Disc.%
  cost_unit     = payable_unit + discount_cost

accienta_sales_total is therefore GROSS of the customer discount, built as sum(price_subtotal) + sum(accienta_discount_cost_line) so it stays exact against Odoo's rounded line amounts. Unit gross profit is gross_unit - cost_unit.

accienta_to_pay_disti_line stays the supplier payable and never carries the customer discount. The per-unit twin was deleted; the field is always x quantity.

**Reason:** The customer discount previously multiplied the cost as well as the price, so both sides shrank together and the margin percentage never moved: giving 25% away looked free. The discount is a variable cost of winning the revenue, so it belongs in the cost of revenue. Counting it in the cost AND netting it off the revenue would subtract it twice, which is why revenue moved to gross. The distributor discount is passed on to the customer by _prepare_base_line_for_taxes_computation, so the billed base is already net of it and Disc.% is measured on that base, not on the full unit price.

**Impact:** Management revenue and cost no longer tie to the GL (they differ by the discount); profit does tie. Migration 19.0.1.0.2 recomputes every line, confirmed orders included. Dormant until the manifest version is bumped at push time.

### Price Books are dedicated models, not product.pricelist

**Decision:** The yearly Price Book in crm-prod is a dedicated pair of models, accienta.price.book and accienta.price.book.line, owned by accienta_products. It is not an extension of product.pricelist. A book holds one company's published USD prices and vendor rates for one year; line fields are product_tmpl_id, price_usd, fee_pct, backend_base, backend_total, with rates as fractions (0.05 = 5%). The name is computed as company plus year, uniqueness is a SQL constraint on (company_id, year), and state is draft / active / locked with at most one active book per company. Importing a price file loads book lines only and has zero live impact. Activation is the switch: it supersedes the current active book to locked and writes price, list_price and rates onto product.template, which every other application reads. Locked means a frozen historical record kept for analysis with no path into a quotation. A book that is not draft cannot be deleted.

**Reason:** The first implementation extended product.pricelist, so every book existed as a pricelist row. Books then appeared in the quotation pricelist field, the customer pricelist field and the Configuration Pricelists list, and had to be suppressed with view domains plus an order constraint. Islam rejected that outright: a book must never create or behave as a pricelist, and the customer pricelist keeps one job only, the currency of the deal. With dedicated models every one of those guards became unnecessary and was deleted, uniqueness became a real SQL constraint (impossible while sharing a table with ordinary pricelists, which carry no year), and the currency field was dropped since book prices are USD by definition.

**Impact:** Deleted: models/product_pricelist.py, models/product_pricelist_item.py, views/product_pricelist_views.xml, the accienta_pricebook_is_book flag, the partner and quotation pricelist domains, the override of the core product_pricelist_action2 domain, and _check_pricelist_is_not_a_pricebook on sale.order. Changing the comodel behind existing many2one columns required clearing stale references before the upgrade could pass.

### accienta_purchase: invoice-to-PO with SO vendor picker

**Decision:** New module accienta_purchase (depends accienta_economics, purchase). Posting a customer invoice auto-creates one confirmed purchase order per PO vendor (no RFQ), grouping invoice lines by the PO vendor chosen on each line's originating sale order; idempotent across re-posts. The PO vendor is picked on the sale order from res.company.accienta_default_vendor_ids (a many-to-many configured in Settings); a 'Show all vendors' boolean toggle widens the picker domain from the default vendors to all suppliers, because Odoo's native 'Search More' cannot escape a field domain. PO lines carry the deal economics (effective SRP, customer discount, distributor discount, backend, fee, DDA) seeded from the sale line and are priced at accienta_cost_unit = effective SRP x (1 - Disc%) x (1 - backend% - fee% - distributor%), editable on the PO without affecting the invoice. purchase.order links back via accienta_source_invoice_id and accienta_source_sale_id.

**Reason:** Islam specified: the PO vendor is chosen on the sale order, the company holds many default vendors, the picker shows defaults with a way to reach all vendors, and posting the invoice creates the PO automatically. The design ports the proven legacy accienta_invoice_purchase to crm-prod economics, replaces the legacy two fixed vendor fields with a many-to-many, and uses the toggle because the native Search More link is domain-bound. sudo on PO creation lets an accountant post without purchase rights.

**Impact:** Customer invoicing now spawns vendor POs automatically; the crm-prod suite is 10 modules. Purchase app is pulled in as a dependency.

### Economics discount model v1.0.5 (disti separate from Disc.%)

**Decision:** Final economics selling model: the quotation unit price is the effective SRP rounded up to a whole unit and never carries the discounts. Disc.% is the native sale.order.line discount field holding the customer discount only. Disti Discount is a separate field (accienta_disti_pct) that reduces the line amount without changing the displayed unit price, by injecting price_unit x (1 - disti%) into the tax base via _prepare_base_line_for_taxes_computation. Line amount = unit price x (1 - disti%) x (1 - Disc.%). The invoice line folds both into its single discount = 100 x (1 - (1-disti)(1-disc)) on the same unit price, so the invoice total equals the order subtotal. Cost/unit = effective SRP x (1 - Disc.%) x (1 - backend% - fee% - disti%). This supersedes the v1.0.4 approach that compounded both discounts into the native discount field (rejected because the native Disc.% column then displayed the combined value instead of the customer discount).

**Reason:** Islam requires Disti and Disc.% to remain two distinct columns, the unit price to stay the SRP sticker (rounded up), and the amount to reflect both discounts. Odoo stores a single discount per line and invoices copy price_unit + discount, so disti is applied to the tax base for the order display and folded into the invoice's single discount for invoice consistency, keeping the two order columns separate.

**Impact:** Order lines show Disti% and native Disc.% separately; the invoice shows one combined discount. Unit price is always an integer. Supersedes decision 6a23517d.

### Economics amount/cost discount routing + integer unit price

**Decision:** accienta_economics: the quotation unit price is the effective SRP rounded UP to a whole unit (ceil of SRP0 x (1-DDA%) x proration). Customer discount (accienta_disc_pct) and distributor discount (accienta_disti_pct) both reduce the customer amount: they are compounded into the native sale.order.line discount field, discount = 100 x (1 - (1-disti)(1-disc)), so subtotal = unit price x (1-disti)(1-disc) and invoices copied from the line stay consistent. Cost/unit = effective SRP x (1 - disc%) x (1 - backend% - fee% - disti%): the customer discount lowers the cost together with the amount, and the distributor discount reduces the amount while remaining in the cost. Disc% is a new custom field; the native Disc.% column now displays the derived compound discount.

**Reason:** Islam specified: unit price rounded up to integer; Amount must reflect DDA, distributor discount and customer discount; customer discount must also reduce cost (cost derived from the discounted price); distributor discount stays in cost. Odoo has a single discount slot and invoices copy price_unit+discount, so compounding both discounts into the native discount is the only invoice-safe way to keep the unit price at the effective SRP while the amount carries both reductions.

**Impact:** Native Disc.% column is derived (edits overwritten); customer discount is entered in the new Disc % field. Gross profit still = unit price - cost, not amount - cost.

### Cascading SRP economics formula (accienta_economics)

**Decision:** accienta_economics owns all channel-economics calculation on the sale order line with a cascading SRP: SRP0 = published SRP (accienta_srp_usd converted to order currency); SRP1 = SRP0 x (1 - DDA%); SRP2 = SRP1 x co-term proration factor. Every rate applies on SRP2: fee amount = SRP2 x fee%, backend amount = SRP2 x backend%, to-pay-distributor = SRP2 x (1 - disti%), cost/unit = SRP2 x (1 - backend% - fee% - disti%). Proration mode is an order-level switch: Overall (order coterm months / 12 for all lines) or Per Line (each line its own prorated months). DDA and distributor discount are manual whole-number percent fields on the line. The line unit price follows SRP2 until the salesperson edits it (tracked via a technical last-auto-price field); cost always derives from SRP2, never from the edited price. Products without SRP fall back to standard_price as cost.

**Reason:** Islam specified the cascade explicitly: DDA and co-term reshape the SRP itself before any rate applies, unlike the legacy formula that applied DDA as a parallel factor. Per-line vs overall proration is a business requirement for mixed-contract orders. Calculations live only in accienta_economics (EconomicsService), keeping accienta_products storage-only per the module boundary decision. Odoo constraint honored: price_unit is a precompute field, so the SRP-following price is assigned from the economics compute instead of extending _compute_price_unit dependencies, which would break line creation.

**Impact:** Quotation lines show SRP, effective SRP, DDA, disti discount, fee/backend amounts, cost and unit gross profit; future PO generation reads accienta_cost_unit as the purchase price.

### Product type restricted to Service only (accienta)

**Decision:** accienta_products redefines product.template.type selection to [('service','Service')] with default 'service', removing Goods and Combo from the product form and everywhere else the selection renders.

**Reason:** The client is a pure service provider (software subscription reselling); Goods/Combo are dead options that invite miscategorised products. Selection redefinition on the inherited field is the only clean mechanism: views cannot filter selection options and core is untouchable. Verified safe: all existing products are services and the import wizard only creates services. Precondition for production: confirm zero consu/combo rows in the prod database before deploying, since such rows would fail validation on write.

**Impact:** Products can only be services; any future need for physical goods requires reverting the selection override in accienta_products.

<!-- /GENERATED:decisions -->

## How to read a decision

!!! info "Each decision states"
    - **Context** — the situation that required a choice.
    - **Decision** — what was chosen.
    - **Reason** — why, over the alternatives.
    - **Impact** — what it affects.
