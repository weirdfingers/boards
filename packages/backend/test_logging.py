#!/usr/bin/env python3
"""
Simple test script to verify structured logging works correctly.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from boards.logging import configure_logging, get_logger, set_request_context, clear_request_context, generate_request_id

def test_basic_logging():
    """Test basic structured logging."""
    print("=== Testing Basic Logging ===")
    
    # Configure for development (human readable)
    configure_logging(debug=True)
    logger = get_logger(__name__)
    
    logger.info("Basic info message")
    logger.info("Message with data", key="value", count=42)
    logger.warning("Warning message", component="test")
    logger.error("Error message", error_code="TEST001", details={"reason": "testing"})

def test_request_context():
    """Test request context logging."""
    print("\n=== Testing Request Context ===")
    
    configure_logging(debug=True)
    logger = get_logger(__name__)
    
    # Set request context
    set_request_context(request_id="req-123", user_id="user-456")
    
    logger.info("Message with context", action="test")
    logger.error("Error with context", error="something failed")
    
    # Clear context
    clear_request_context()
    logger.info("Message after clearing context")

def test_production_logging():
    """Test production JSON logging."""
    print("\n=== Testing Production Logging (JSON) ===")
    
    # Configure for production (JSON)
    configure_logging(debug=False)
    logger = get_logger(__name__)
    
    set_request_context(user_id="user-789")
    
    logger.info("Production log message", 
                component="api", 
                operation="user_login",
                duration_ms=150,
                success=True)
    
    logger.error("Production error message",
                 component="database",
                 operation="query",
                 error="connection timeout",
                 query="SELECT * FROM users",
                 duration_ms=5000)

def test_request_id_generation():
    """Test the new compact request ID generation."""
    print("\n=== Testing Request ID Generation ===")
    
    # Generate several request IDs to show format
    print("Generated request IDs:")
    for i in range(5):
        req_id = generate_request_id()
        print(f"  {i+1}: {req_id} (length: {len(req_id)})")
        time.sleep(0.001)  # Small delay to show different timestamps
    
    print(f"Compare to UUID length: {len('550e8400-e29b-41d4-a716-446655440000')} chars")

if __name__ == "__main__":
    test_basic_logging()
    test_request_context()  
    test_production_logging()
    test_request_id_generation()
    print("\n=== Logging Tests Complete ===")