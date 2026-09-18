import base64
from pathlib import Path

from src.image_order_service import OrderRequest, fulfill_order


class FakeResponse:
    class Item:
        b64_json = base64.b64encode(b"png-bytes").decode()

    data = [Item()]


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return FakeResponse()


def test_paid_in_stock_order_is_fulfilled_and_receipt_is_written(tmp_path: Path):
    client = FakeClient()
    receipt = fulfill_order(
        OrderRequest("o-7", "blue mug", paid=True, stock=1), tmp_path, client
    )
    assert receipt.state == "fulfilled"
    assert Path(receipt.image_path).read_bytes() == b"png-bytes"
    assert (tmp_path / "o-7.json").exists()
    assert client.prompts == ["Studio product photo of blue mug, white background"]


def test_unpaid_order_does_not_call_image_api(tmp_path: Path):
    client = FakeClient()
    receipt = fulfill_order(OrderRequest("o-8", "blue mug", paid=False, stock=1), tmp_path, client)
    assert receipt.state == "rejected"
    assert client.prompts == []
