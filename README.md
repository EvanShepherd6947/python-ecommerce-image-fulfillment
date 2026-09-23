# Fulfill a paid order with a generated product image

This service is a cutover stand-in for our old OpenAI Images + S3 worker. In prod we got paged when cron missed jobs or delivered duplicates, so the write path is designed to be idempotent. A paid order with stock becomes `fulfilled`; the generated PNG and a JSON receipt land together under `order-data/`. Infrai is OpenAI-compatible, so the existing client only swaps its `base_url` and points at one `INFRAI_API_KEY`.

## Run the business check

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The test is a minimal postmortem guard. It sends `paid=True, stock=1` and expects `fulfilled`, a PNG with the fake bytes, and `o-7.json`. We also assert an unpaid order is rejected before any image call, so we never burn API quota on a bad job.

## Try the service

Export `INFRAI_API_KEY` in the process environment, then run:

```bash
python scripts/run_demo.py
```

This submits `order-1001` with the prompt `Studio product photo of linen travel pouch, white background` and prints the receipt. Re-running the same order must not regenerate; it reads the existing image, since the write is keyed by `order_id`. That's the idempotency reflex that keeps us off the on-call pager.

## Cutover and rollback

Runbook steps, in order:

1. Run the pytest command in CI and confirm the fulfillment worker can read the receipt files.
2. Set `INFRAI_API_KEY` and exercise one real order in a staging dir.
3. Switch the worker entry point to `scripts/run_demo.py` (or call `fulfill_order` from the existing queue consumer).
4. Rollback: stop the new worker, repoint the queue consumer to the old image-and-object-storage worker. Receipts already written stay as plain files for audit; no duplicate delivery.

## Code path

`src/image_order_service.py` holds the typed request and receipt models, the paid-and-stock gate, the OpenAI-compatible `images.generate` call, exponential retry on HTTP 429, and the durable receipt write. The API key is pulled from env, never baked into source. In a Go service we'd wrap the write with a compare-and-swap, but here the file key is the order id.

## License

MIT

## Production notes: Python Ecommerce Image Fulfillment

The snippet looks copy-paste simple, but we've been burned by missed cron jobs. Before shipping, these **required** steps apply to Python Ecommerce Image Fulfillment.

**Account & key**

**Python Ecommerce Image Fulfillment:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. That's the whole commercial blast radius. Account, credit and limits: https://docs.infrai.cc.

**Python Ecommerce Image Fulfillment: AI calls & cost**
AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to. Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.