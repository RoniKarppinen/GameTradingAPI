"""Auxiliary services for trade analytics."""

import requests
from flask import Flask, jsonify

app = Flask(__name__)

class TradeAnalyticsService:
    """Provides summary metrics derived from trade data."""

    _cached_summary = None

    @staticmethod
    def fetch_trade_data():
        """Fetch trade data by calling the API server instead of direct DB access."""
        try:
            response = requests.get("http://127.0.0.1:5000/api/trades/", timeout=2)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return []

    @staticmethod
    def count_successful_trades(trades):
        """Count successful trades from a trade payload list."""
        return sum(1 for trade in trades if trade.get("status") == "Accepted")

    @classmethod
    def invalidate_cache(cls):
        """Invalidate cached trade summary values."""
        cls._cached_summary = None

    @classmethod
    def successful_trade_summary(cls):
        """Return the successful trade count together with total trade count."""
        if cls._cached_summary is not None:
            return dict(cls._cached_summary)

        trades = cls.fetch_trade_data()
        summary = {
            "successful_trades": cls.count_successful_trades(trades),
            "total_trades": len(trades),
        }

        cls._cached_summary = summary

        return dict(summary)

@app.route("/api/analytics/successful-count/", methods=["GET"])
def get_successful_count():
    return jsonify(TradeAnalyticsService.successful_trade_summary()), 200

@app.route("/api/analytics/invalidate/", methods=["POST"])
def invalidate():
    TradeAnalyticsService.invalidate_cache()
    return "", 204

if __name__ == "__main__":
    app.run(port=5001, debug=True)
