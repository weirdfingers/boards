"""
Compatibility shim: re-export models from boards.dbmodels
This file remains to avoid breaking existing imports like `from boards.database.models import ...`.
"""

from boards.dbmodels import (  # noqa: F401
    Base,
    Tenants,
    ProviderConfigs,
    Users,
    Boards,
    LoraModels,
    BoardMembers,
    Generations,
    CreditTransactions,
    target_metadata,
)
