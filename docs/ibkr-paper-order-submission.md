# IBKR Paper Order Submission

Day Trade Maker can optionally submit an approved, risk-checked audit-only order intent to an Interactive Brokers paper account. This is disabled by default and is intentionally separate from live trading.

## Safety boundary

- `PaperOrderIntent` remains an audit artifact. It records the user's intended paper-mode order and always keeps `submitted_to_broker=false`.
- `PaperBrokerOrderSubmission` is the separate broker side-effect artifact created only after the paper-account submission gates pass.
- Live trading is not implemented or supported in this workflow.
- Resetting local audit state does not submit, cancel, or otherwise touch IBKR orders.

## Required environment

Start with all defaults disabled. Only enable submission when you are intentionally testing against an IBKR paper account.

Required variables/prerequisites for real paper submission:

- the backend environment has the optional `ib_async` package available;
- IBKR Gateway/TWS is logged into the target paper account;
- the environment is configured as below.

```bash
DAY_TRADE_MAKER_IBKR_HOST=127.0.0.1
DAY_TRADE_MAKER_IBKR_PORT=4002        # IBKR Gateway paper default; TWS paper commonly uses 7497
DAY_TRADE_MAKER_IBKR_CLIENT_ID=1
DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_ENABLED=true
DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_READER=ib_async
DAY_TRADE_MAKER_IBKR_PAPER_ACCOUNT_ID=DU1234567
DAY_TRADE_MAKER_IBKR_PAPER_ORDER_SUBMISSION_ENABLED=true
DAY_TRADE_MAKER_IBKR_PAPER_ORDER_CONFIRMATION_PHRASE="SUBMIT IBKR PAPER ORDER"

# Required before exposing side-effecting broker endpoints beyond trusted local dev.
DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_AUTH_REQUIRED=true
DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_ADMIN_TOKEN="replace-with-random-admin-token"
DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_CSRF_TOKEN="replace-with-random-csrf-token"
```

Notes:

- `DAY_TRADE_MAKER_IBKR_PAPER_ACCOUNT_ID` must match the loaded account snapshot exactly and should use IBKR's paper-account `DU...` shape.
- Missing account IDs, live-looking `U...` IDs, and mismatched IDs keep broker order operations unavailable.
- The backend sets the verified paper account id on the IBKR order before `placeOrder`.
- If `DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_AUTH_REQUIRED=true`, the submission and status-refresh endpoints fail closed unless both server-side tokens are configured and the request includes matching `Authorization: Bearer ...` and `X-CSRF-Token` headers.
- The frontend exposes in-memory token fields in the IBKR paper submission panel. Leave them blank only for trusted local development where the backend auth gate remains disabled.

## Manual smoke flow

1. Start IBKR Gateway or TWS logged into the target paper account.
2. Start the backend with the paper submission env vars above.
3. Load `GET /api/broker/safety-summary`.
4. Confirm:
   - `current_execution_mode="paper_broker"`
   - `paper_broker_submission_enabled=true`
   - `broker_order_operation_available=true`
   - `live_broker_submission_enabled=false`
   - `account_id` matches `DAY_TRADE_MAKER_IBKR_PAPER_ACCOUNT_ID`
5. In the UI, create or restore the research chain:
   - transcript
   - approved strategy
   - imported market data
   - backtest
   - passed risk check
   - audit-only paper order intent
6. Enter the broker side-effect admin token and CSRF token in the UI if `DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_AUTH_REQUIRED=true`.
7. Type the exact phrase: `SUBMIT IBKR PAPER ORDER`.
8. Click `Submit to IBKR paper account`.
9. Verify the returned broker order id/status in the UI and in the exported audit snapshot.
10. To refresh status later, click `Refresh IBKR paper order status`; this uses the same paper-account safety gates and persists `latest_broker_order_status`, `broker_status_checked_at`, and the raw status response on the existing submission artifact.

## Emergency disable

To disable the broker side effect:

1. Set `DAY_TRADE_MAKER_IBKR_PAPER_ORDER_SUBMISSION_ENABLED=false` or unset it.
2. Restart the backend.
3. Confirm `GET /api/broker/order-submission-capability` returns `broker_order_operation_available=false`.
4. Confirm the UI shows `IBKR paper order submission disabled`.

## Known limits

- The first submitter slice is narrow: SMART/USD stock market and limit orders only.
- The backend writes a durable `pending_broker_submission` record to the local audit snapshot before calling `placeOrder`; retries for the same order intent are blocked while any pending, submitted, or failed submission record exists.
- If submission does not finish cleanly, the record is marked `submission_failed_requires_manual_review`; inspect IBKR/TWS and the audit snapshot before deciding any manual follow-up. Do not simply retry the same intent.
- Status refresh is explicit/operator-triggered. It does not place or cancel orders; it connects read-only to IBKR, asks for currently open trades, updates the existing submission record, and may report `unknown` if IBKR no longer returns that order in open trades.
- Side-effecting broker endpoints support an optional admin bearer-token plus CSRF-token gate. Keep the backend bound to trusted local development if `DAY_TRADE_MAKER_BROKER_SIDE_EFFECT_AUTH_REQUIRED=false`; set it to `true` before exposing beyond trusted local dev.
