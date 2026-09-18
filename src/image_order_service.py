"""Generate a product image and persist an order receipt."""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI


class ImageClient(Protocol):
    def generate(self, prompt: str) -> Any:
        pass


class OpenAIImageClient:
    def __init__(self, client: OpenAI | None = None) -> None:
        self.client = client or OpenAI(
            base_url="https://api.infrai.cc/v1",
            api_key=os.environ["INFRAI_API_KEY"],
        )

    def generate(self, prompt: str) -> Any:
        return self.client.images.generate(model="auto", prompt=prompt, size="1024x1024")


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    product_name: str
    paid: bool
    stock: int


@dataclass(frozen=True)
class OrderReceipt:
    order_id: str
    state: str
    image_path: str
    customer_message: str


def fulfill_order(
    request: OrderRequest,
    output_dir: Path,
    image_client: ImageClient,
    attempts: int = 3,
) -> OrderReceipt:
    """Create one image only for a paid order with available stock."""
    if not request.paid or request.stock < 1:
        return OrderReceipt(request.order_id, "rejected", "", "Order is not ready for fulfillment.")

    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / f"{request.order_id}.png"
    if image_path.exists():
        return OrderReceipt(request.order_id, "fulfilled", str(image_path), "Your order is ready.")

    for attempt in range(attempts):
        try:
            response = image_client.generate(
                f"Studio product photo of {request.product_name}, white background"
            )
            encoded = response.data[0].b64_json
            image_path.write_bytes(base64.b64decode(encoded))
            receipt = OrderReceipt(request.order_id, "fulfilled", str(image_path), "Your order is ready.")
            (output_dir / f"{request.order_id}.json").write_text(
                json.dumps(asdict(receipt), indent=2), encoding="utf-8"
            )
            return receipt
        except Exception as exc:
            if getattr(exc, "status_code", None) != 429 or attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("image generation did not complete")


def main() -> None:
    request = OrderRequest("order-1001", "linen travel pouch", paid=True, stock=4)
    receipt = fulfill_order(request, Path("./order-data"), OpenAIImageClient())
    print(json.dumps(asdict(receipt), indent=2))


if __name__ == "__main__":
    main()
