"""Orderful target class."""

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.helpers.capabilities import AlertingLevel
from hotglue_singer_sdk.target_sdk.target import TargetHotglue

from target_orderful.sinks import PurchaseOrdersSink


class TargetOrderful(TargetHotglue):
    """Singer target for Orderful EDI transactions."""

    SINK_TYPES = [
        PurchaseOrdersSink,
    ]
    name = "target-orderful"
    alerting_level = AlertingLevel.ERROR

    config_jsonschema = th.PropertiesList(
        th.Property("api_key", th.StringType, required=True),
        th.Property(
            "sender_isa_id",
            th.StringType,
            required=False,
            description=(
                "Default ISA ID of the party sending the 850 (the buyer). "
                "Can be overridden per record via the sender_isa_id field."
            ),
        ),
        th.Property(
            "receiver_isa_id",
            th.StringType,
            required=False,
            description=(
                "Default ISA ID of the party receiving the 850 (the supplier). "
                "Can be overridden per record via the receiver_isa_id field."
            ),
        ),
        th.Property(
            "stream",
            th.StringType,
            required=False,
            description="Orderful transaction stream: TEST (default) or LIVE.",
        ),
    ).to_dict()


if __name__ == "__main__":
    TargetOrderful.cli()
