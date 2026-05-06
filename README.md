# target-orderful

Singer target for [Orderful](https://orderful.com) — sends EDI 850 Purchase Order transactions via the Orderful v3 API.

Built with the [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK) for Singer Targets.

---

## Installation

```bash
pip install target-orderful
```

Or directly from this repo:

```bash
pip install git+https://github.com/hotgluexyz/target-orderful.git
```

---

## Configuration

Create a `config.json` with the following fields:

| Field | Required | Description |
|---|---|---|
| `api_key` | Yes | Orderful API key (from Organization Settings → API Credentials) |
| `sender_isa_id` | No | Default ISA ID of the party sending the 850 (the buyer). Can be overridden per record. |
| `receiver_isa_id` | No | Default ISA ID of the party receiving the 850 (the supplier). Can be overridden per record. |
| `stream` | No | Orderful transaction stream: `TEST` (default) or `LIVE` |

Example `config.json`:

```json
{
  "api_key": "your-api-key-here",
  "sender_isa_id": "BUYERISA",
  "receiver_isa_id": "SUPPLIERISA",
  "stream": "TEST"
}
```

---

## Authentication

The Orderful API uses a static API key passed via the `orderful-api-key` request header. Obtain it from the Orderful UI under **Settings → API Credentials**.

---

## Supported Streams

| Stream | Description |
|---|---|
| `purchase_orders` | EDI 850 Purchase Orders — one record per PO with line items embedded |

### Record shape for `purchase_orders`

The ETL (mapping layer between your ERP and this target) should produce records in this shape:

```json
{
  "purchase_order_number": "EDI-PO-001",
  "purchase_order_date": "20260501",
  "sender_isa_id": "BUYERISA",
  "receiver_isa_id": "SUPPLIERISA",
  "line_items": [
    {
      "line_number": "1",
      "quantity": "10",
      "unit_price": "45.00",
      "sku": "MY-SKU-001",
      "description": "Widget A",
      "uom": "EA"
    }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `purchase_order_number` | Yes | Becomes `businessNumber` in Orderful UI. Max 10 chars for some trading partners. |
| `purchase_order_date` | Yes | Accepts `YYYYMMDD`, `YYYY-MM-DD`, or `YYYY-MM-DDTHH:MM:SS` |
| `sender_isa_id` | No | Overrides config `sender_isa_id` for this record |
| `receiver_isa_id` | No | Overrides config `receiver_isa_id` for this record |
| `line_items[].line_number` | No | EDI PO101; auto-incremented from 1 if omitted |
| `line_items[].quantity` | Yes | String or number |
| `line_items[].unit_price` | Yes | String or number |
| `line_items[].sku` | Yes | Product SKU — maps to `SK` qualifier in EDI |
| `line_items[].description` | No | Free-form product description (PID segment) |
| `line_items[].uom` | No | Unit of measure code, default `EA` |

---

## Usage

Pipe a Singer-format file into the target:

```bash
cat sample_payload/data.singer | target-orderful --config config.json
```

Or chain a tap through an ETL mapper:

```bash
tap-erp --config tap_config.json | etl-mapper | target-orderful --config config.json
```

---

## Developer Resources

```bash
# Create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate

# Install the target in editable mode
pip install -e .

# Install ruff for linting
pip install ruff

# Run linter
ruff check .

# Verify the CLI
target-orderful --version
target-orderful --about

# Run the sample payload against Orderful
cat sample_payload/data.singer | target-orderful --config .secrets/config.json \
    > .secrets/output.singer 2> .secrets/output.singer.log
```
