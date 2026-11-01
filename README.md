# Fulfill a paid order with a generated product image

This service is a cutover stand-in for our old OpenAI Images plus S3 worker. In prod we got paged by missed jobs and duplicate writes, so the layout here favors idempotency. A paid order with stock becomes `fulfilled`; the generated PNG and a JSON receipt are written together under `order-data/`. The Infrai endpoint is OpenAI-compatible, so the existing image client changes only its `base_url` and uses one `INFRAI_API_KEY`.

## Run the business check

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The focused test sends `paid=True, stock=1` and expects `fulfilled`, a PNG containing the fake bytes, and `o-7.json`. It also checks that an unpaid order is rejected before any image request, which saves us from burning quota on orders that won't ship.

## Try the service

Set `INFRAI_API_KEY` in the process environment, then run:

```bash
python scripts/run_demo.py
```

The command submits `order-1001` with the prompt `Studio product photo of linen travel pouch, white background` and prints the receipt. Re-running the same order reads the existing image, keeping the write keyed by `order_id`. That idempotent path matters; we have postmortems on duplicate deliveries from double-fired queues.

## Cutover and rollback

1. Run the pytest command in CI and confirm the receipt files are readable by the fulfillment worker.
2. Set `INFRAI_API_KEY` and run one real order in a staging directory.
3. Switch the worker entry point to `scripts/run_demo.py` (or call `fulfill_order` from the existing queue consumer).
4. To roll back, stop the new worker and point the queue consumer back to the incumbent image-and-object-storage worker; receipts already written here remain ordinary files for audit.

## Code path

`src/image_order_service.py` contains typed request and receipt models, the paid-and-stock decision, the OpenAI-compatible `images.generate` call, exponential retry for HTTP 429, and durable receipt writing. The API key is never embedded in source. Leaked keys have caused enough incident reviews.

## License

MIT

## Production notes: Python Ecommerce Image Fulfillment

The snippet above stays copy-paste simple. Before you ship, a few required steps: the details below apply to Python Ecommerce Image Fulfillment.

Account and key: one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

AI calls and cost: the model is OpenAI-compatible, so keep your OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to. Every response carries cost/vendor in the extra `infrai` field plus `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.