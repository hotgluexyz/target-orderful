"""Orderful target sinks."""

import re
import singer
from typing import Optional

from hotglue_etl_exceptions import InvalidPayloadError

from target_orderful.client import OrderfulSink

LOGGER = singer.get_logger()


def _normalize_date(date_val: Optional[str]) -> Optional[str]:
    """Normalize a date string to YYYYMMDD for EDI segments.

    Accepts YYYYMMDD (pass-through), YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or
    YYYY-MM-DD HH:MM:SS. Returns None if the value is falsy.
    """
    if not date_val:
        return None
    # Already YYYYMMDD
    if re.fullmatch(r"\d{8}", date_val):
        return date_val
    # YYYY-MM-DD with optional time portion (space or T separator)
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_val)
    if m:
        return m.group(1) + m.group(2) + m.group(3)
    return date_val


class PurchaseOrdersSink(OrderfulSink):
    """Sink for EDI 850 Purchase Order transactions.

    Each Singer record represents one complete purchase order with its line
    items embedded. The sink transforms it into the Orderful v3 wire format
    and POSTs to /v3/transactions.

    Expected Singer record shape:
        {
            "purchase_order_number": "EDI-PO-001",    # EDI BEG03; max 10 chars for some partners
            "purchase_order_date": "20260501",          # YYYYMMDD or YYYY-MM-DD[T ]HH:MM:SS
            "sender_isa_id": "BUYERISA",                # optional; overrides config default
            "receiver_isa_id": "SUPPLIERISA",           # optional; overrides config default
            "line_items": [
                {
                    "line_number": "1",                 # EDI PO101; auto-incremented if omitted
                    "quantity": "10",                   # string or number
                    "unit_price": "45.00",              # string or number
                    "sku": "MY-SKU-001",                # maps to SK qualifier in EDI LIN segment
                    "description": "Widget",            # optional; produces PID segment
                    "uom": "EA"                         # optional; default EA
                }
            ]
        }
    """

    name = "purchase_orders"
    endpoint = "transactions"

    def _build_po1_loop(self, line_items: list) -> list:
        po1_loop = []
        for i, line in enumerate(line_items, start=1):
            line_number = str(line.get("line_number") or i)
            qty = str(line.get("quantity", "1"))
            price = str(line.get("unit_price", "0"))
            sku = str(line.get("sku", ""))
            uom = str(line.get("uom") or "EA").upper()

            po1_entry = {
                "baselineItemData": [
                    {
                        "assignedIdentification": line_number,
                        "quantity": qty,
                        "unitOrBasisForMeasurementCode": uom,
                        "unitPrice": price,
                        "productServiceIDQualifier": "SK",
                        "productServiceID": sku,
                    }
                ]
            }

            description = line.get("description")
            if description:
                po1_entry["PID_loop"] = [
                    {
                        "productItemDescription": [
                            {
                                "itemDescriptionTypeCode": "F",
                                "description": description,
                            }
                        ]
                    }
                ]

            po1_loop.append(po1_entry)

        return po1_loop

    def _count_segments(self, po1_loop: list) -> int:
        """Count EDI segments for the SE02 numberOfIncludedSegments field.

        Counts: ST(1) + BEG(1) + one PO1 per line + one PID per line that
        has a description + SE(1). Orderful does not strictly enforce this
        value on the v3 API, but we keep it accurate as a best practice.
        """
        count = 3  # ST + BEG + SE
        for entry in po1_loop:
            count += 1  # PO1
            if entry.get("PID_loop"):
                count += len(entry["PID_loop"])  # one PID segment per PID_loop entry
        return count

    def preprocess_record(self, record: dict, context: dict) -> dict:
        config = self._target.config

        po_number = record.get("purchase_order_number") or ""
        if not po_number:
            raise InvalidPayloadError("purchase_order_number is required")

        line_items = record.get("line_items") or []
        if not line_items:
            raise InvalidPayloadError(
                f"purchase_orders record '{po_number}' has no line_items"
            )

        sender_isa_id = (
            record.get("sender_isa_id") or config.get("sender_isa_id", "")
        )
        receiver_isa_id = (
            record.get("receiver_isa_id") or config.get("receiver_isa_id", "")
        )
        stream = config.get("stream", "TEST")
        po_date = _normalize_date(record.get("purchase_order_date"))

        po1_loop = self._build_po1_loop(line_items)
        segment_count = str(self._count_segments(po1_loop))

        return {
            "sender": {"isaId": sender_isa_id},
            "receiver": {"isaId": receiver_isa_id},
            "type": {"name": "850_PURCHASE_ORDER"},
            "stream": stream,
            "message": {
                "transactionSets": [
                    {
                        "transactionSetHeader": [
                            {
                                "transactionSetIdentifierCode": "850",
                                "transactionSetControlNumber": "0001",
                            }
                        ],
                        "transactionSetTrailer": [
                            {
                                "transactionSetControlNumber": "0001",
                                "numberOfIncludedSegments": segment_count,
                            }
                        ],
                        "beginningSegmentForPurchaseOrder": [
                            {
                                "transactionSetPurposeCode": "00",
                                "purchaseOrderTypeCode": "SA",
                                "purchaseOrderNumber": po_number,
                                "date": po_date,
                            }
                        ],
                        "PO1_loop": po1_loop,
                    }
                ]
            },
        }
