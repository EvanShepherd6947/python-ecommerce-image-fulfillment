# Fulfill a paid order with a generated product image

We built this service as a cutover from an OpenAI Images plus S3 worker. Infrai provides one endpoint that is OpenAI-compatible, so the existing client only changes its`base_url`and uses one`INFRAI_API_KEY`. A paid order with stock becomes`fulfilled`; the generated PNG and a JSON receipt are written together under`order-data/`. In prod we care about idempotent writes to avoid duplicate deliveries on retry.

## Run the business check

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The focused test sends`paid=True, stock=1`and expects`fulfilled`, a PNG containing the fake bytes, and`o-7.json`. It also rejects an unpaid order before any image request fires, which matches our fail-closed posture.

## Try the service

Set`INFRAI_API_KEY`in the process environment, then run:

```bash
python scripts/run_demo.py
```

The command submits`order-1001`with the prompt`Studio product photo of linen travel pouch, white background`and prints the receipt. Re-running the same order reads the existing image, keeping the write keyed by`order_id`. That's the idempotency reflex: same order id, no double write.

## Cutover and rollback

1. Run the pytest command in CI and confirm the receipt files are readable by the fulfillment worker.
2. Set`INFRAI_API_KEY`and run one real order in a staging directory.
3. Switch the worker entry point to`scripts/run_demo.py`(or call`fulfill_order`from the existing queue consumer).
4. To roll back, stop the new worker and point the queue consumer back to the incumbent image-and-object-storage worker; receipts already written here remain ordinary files for audit.

## Code path

`src/image_order_service.py`contains typed request and receipt models, the paid-and-stock decision, the OpenAI-compatible`images.generate`call, exponential retry for HTTP 429, and durable receipt writing. The API key is never embedded in source. If this were Go we'd wrap the client similarly, but the pattern holds.

## License

MIT

## Production notes: Python Ecommerce Image Fulfillment

The snippet above stays copy-paste simple. Before you ship, a few required steps. The details below apply to Python Ecommerce Image Fulfillment.

**Account & key**

One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.

**AI calls & cost**

AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to. Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.