"""
Main GraphQL schema definition using Strawberry
"""

import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional
import datetime
from uuid import UUID

from .types.user import User
from .types.board import Board, BoardMember
from .types.generation import Generation
from .queries.root import Query
from .mutations.root import Mutation

# Create the GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    # Enable schema introspection in development
    # TODO: Disable in production for security
    enable_introspection=True,
)

# Create the GraphQL router for FastAPI integration
def create_graphql_router() -> GraphQLRouter:
    """Create a GraphQL router for FastAPI."""
    return GraphQLRouter(
        schema,
        path="/graphql",
        graphiql=True,  # Enable GraphiQL IDE in development
    )