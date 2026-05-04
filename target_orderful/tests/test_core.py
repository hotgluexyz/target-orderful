"""Core tests for target-orderful."""

import json
import os

import pytest
from hotglue_singer_sdk.testing import get_standard_target_tests

from target_orderful.target import TargetOrderful

SECRETS_PATH = os.path.join(os.path.dirname(__file__), "../../.secrets/config.json")


@pytest.fixture
def config():
    if not os.path.exists(SECRETS_PATH):
        pytest.skip("No .secrets/config.json found — skipping live tests.")
    with open(SECRETS_PATH) as f:
        return json.load(f)


def test_standard_target_tests(config):
    tests = get_standard_target_tests(TargetOrderful, config=config)
    for test in tests:
        test()
