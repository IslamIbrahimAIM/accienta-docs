# Architecture

A high-level view of the Accienta Odoo Enterprise solution. This page
describes structure and intent, not source code.

## Solution overview

```mermaid
flowchart LR
    Users[Users] --> Odoo[Odoo Enterprise 19 Enterprise]
    Odoo --> DB[(Database)]
    Odoo --> Custom[Custom applications]
```

## Module map

<!-- GENERATED:module-map -->
```mermaid
flowchart LR
    accienta_base --> accienta_crm
    accienta_products --> accienta_economics
    accienta_sales --> accienta_economics
    accienta_coa --> accienta_ksa
    accienta_base --> accienta_org
    accienta_base --> accienta_products
    accienta_economics --> accienta_purchase
    accienta_base --> accienta_reports
    accienta_base --> accienta_sales
    accienta_coa --> accienta_uae
```
<!-- /GENERATED:module-map -->

## Design principles

- Standard Odoo is extended, never modified.
- Each custom application owns a clear area of the business.
- Modules communicate through supported, stable interfaces.

For the decisions behind this architecture, see [Decisions](decisions.md).
