from typing import Any, Dict, List, Optional

import requests


def is_midtrans_enabled(config: Dict[str, Any]) -> bool:
    return bool(config.get("MIDTRANS_SERVER_KEY") and config.get("MIDTRANS_CLIENT_KEY"))


def get_snap_url(is_production: bool) -> str:
    if is_production:
        return "https://app.midtrans.com/snap/snap.js"
    return "https://app.sandbox.midtrans.com/snap/snap.js"


def create_snap_token(
    config: Dict[str, Any],
    order_id: str,
    gross_amount: int,
    customer: Dict[str, Any],
    item_details: Optional[List[Dict[str, Any]]] = None,
) -> str:
    base_url = "https://app.midtrans.com" if config["MIDTRANS_IS_PRODUCTION"] else "https://app.sandbox.midtrans.com"

    payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": gross_amount,
        },
        "customer_details": {
            "first_name": customer.get("name", "Pelanggan"),
            "email": customer.get("email", "pelanggan@example.com"),
        },
        "item_details": item_details
        or [
            {
                "id": "tagihan",
                "price": gross_amount,
                "quantity": 1,
                "name": "Tagihan Listrik",
            }
        ],
    }

    response = requests.post(
        f"{base_url}/snap/v1/transactions",
        auth=(config["MIDTRANS_SERVER_KEY"], ""),
        json=payload,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    token = data.get("token")
    if not token:
        raise RuntimeError("Snap token not returned")
    return token
