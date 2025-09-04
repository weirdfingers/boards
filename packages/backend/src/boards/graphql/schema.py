"""
Main GraphQL schema definition using Strawberry
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from .mutations.root import Mutation
from .queries.root import Query

# Create the GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    # Note: Introspection is enabled by default in strawberry
    # TODO: Disable in production for security by using extensions
)

# Create the GraphQL router for FastAPI integration
def create_graphql_router() -> GraphQLRouter:
    """Create a GraphQL router for FastAPI."""
    return GraphQLRouter(
        schema,
        path="/graphql",
        graphiql=True,  # Enable GraphiQL IDE in development
    )
