# type: ignore[reportMissingImports]

"""
Compatibility shim: re-export models from boards.dbmodels
This file remains to avoid breaking existing imports like `from boards.database.models import ...`.
"""

from boards.dbmodels import (  # noqa: F401
    Base,
    BoardMembers,
    Boards,
    CreditTransactions,
    Generations,
    LoraModels,
    ProviderConfigs,
    Tenants,
    Users,
    target_metadata,
)
