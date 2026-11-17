"""V2 deterministic auction and atomic settlement (ADR-005 §2).

Implements REQ-ADS-ARCH-005 through REQ-ADS-ARCH-012 and
REQ-ADS-FR-005 through REQ-ADS-FR-008. The public boundary separates pure
selection from persisted budget authority and canonical audit evidence.
"""

from .engine import AuctionChoice, choose_winner
from .ledger import InsufficientBudget, Ledger, LedgerError, RequestConflict
from .models import Bid, BidError, validate_bids

__all__ = [
    "Bid", "BidError", "validate_bids", "AuctionChoice", "choose_winner",
    "Ledger", "LedgerError", "RequestConflict", "InsufficientBudget",
]
