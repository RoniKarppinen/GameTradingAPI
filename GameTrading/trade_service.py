"""Auxiliary services for trade analytics."""

from GameTrading.db import Trade


class TradeAnalyticsService:
    """Provides summary metrics derived from trade data."""

    @staticmethod
    def fetch_trade_data():
        """Fetch trade data in the same shape used by the trade collection endpoint."""
        trades = Trade.query.all()
        return [
            {
                "id": trade.id,
                "status": trade.status,
                "sender_game_id": trade.sender_game_id,
                "receiver_game_id": trade.receiver_game_id,
            }
            for trade in trades
        ]

    @staticmethod
    def count_successful_trades(trades):
        """Count successful trades from a trade payload list."""
        return sum(1 for trade in trades if trade.get("status") == "Accepted")

    @classmethod
    def successful_trade_summary(cls):
        """Return the successful trade count together with total trade count."""
        trades = cls.fetch_trade_data()
        return {
            "successful_trades": cls.count_successful_trades(trades),
            "total_trades": len(trades),
        }
