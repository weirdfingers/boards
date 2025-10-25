"""
Main GraphQL schema definition using Strawberry
"""

from typing import Any

import strawberry
from fastapi import Request
from graphql import validate_schema as gql_validate_schema
from strawberry.fastapi import GraphQLRouter

from ..logging import get_logger
from .mutations.root import Mutation
from .queries.root import Query

# Import types to ensure they're registered with Strawberry

logger = get_logger(__name__)

# Create the GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    # Note: Introspection is enabled by default in strawberry
    # TODO: Disable in production for security by using extensions
)


def validate_schema() -> None:
    """Validate the GraphQL schema at startup.

    This ensures that all type references can be resolved and catches
    circular reference errors early, causing the server to fail fast
    rather than returning 404s at runtime.

    Raises:
        Exception: If the schema is invalid or has unresolved types
    """
    try:
        # Convert to GraphQL core schema to trigger full validation
        graphql_schema = schema._schema

        # Validate the schema structure
        errors = gql_validate_schema(graphql_schema)
        if errors:
            error_messages = [str(e) for e in errors]
            raise Exception(f"GraphQL schema validation failed: {'; '.join(error_messages)}")

        # Check that introspection query works (catches most resolution issues)
        from graphql import get_introspection_query, graphql_sync

        introspection_query = get_introspection_query()
        result = graphql_sync(graphql_schema, introspection_query)

        if result.errors:
            error_messages = [str(e) for e in result.errors]
            raise Exception(f"GraphQL introspection failed: {'; '.join(error_messages)}")

        logger.info("GraphQL schema validation successful")

    except Exception as e:
        logger.error("GraphQL schema validation failed", error=str(e))
        raise


# Create the GraphQL router for FastAPI integration
def create_graphql_router() -> GraphQLRouter[dict[str, Any], None]:
    """Create a GraphQL router for FastAPI."""

    async def get_context(request: Request) -> dict[str, Any]:
        """Get the context for GraphQL resolvers."""
        return {
            "request": request,
        }

    return GraphQLRouter(
        schema,
        path="/graphql",
        graphiql=True,  # Enable GraphiQL IDE in development
        context_getter=get_context,
    )
