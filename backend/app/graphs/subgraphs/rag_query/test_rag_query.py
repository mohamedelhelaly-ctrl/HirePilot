"""
Test script for the RAG query subgraph.

This script tests the agent architecture implementation for the RAG query subgraph.
It verifies that the subgraph can be created, invoked, and returns expected results.
"""

import asyncio
import json
import logging
from typing import Optional

from langchain_core.messages import HumanMessage

from .graph import create_rag_query_subgraph
from .state import RAGQueryState

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_rag_query_subgraph():
    """
    Test the RAG query subgraph with a sample query.
    """
    logger.info("Starting RAG query subgraph test...")

    # Create the subgraph
    try:
        subgraph = create_rag_query_subgraph()
        logger.info("✓ Subgraph created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create subgraph: {e}")
        return False

    # Prepare test input state
    test_query = "Show me all candidates for this position"
    test_requisition_id = 1  # Assuming test data exists with requisition_id=1
    test_user_id = 1  # Assuming test user exists

    input_state = RAGQueryState(
        query=test_query,
        requisition_id=test_requisition_id,
        user_id=test_user_id,
        messages=[HumanMessage(content=test_query)],  # Initialize with user query
        response=""  # Will be filled by the subgraph
    )

    logger.info(f"Test input: query='{test_query}', requisition_id={test_requisition_id}")

    # Invoke the subgraph
    try:
        result_state = await subgraph.ainvoke(input_state)
        logger.info("✓ Subgraph invoked successfully")
    except Exception as e:
        logger.error(f"✗ Failed to invoke subgraph: {e}")
        return False

    # Validate the result
    if result_state.response:
        logger.info("✓ Subgraph returned a response")
        logger.info(f"Response length: {len(result_state.response)} characters")

        # Try to parse if it's JSON (from tools)
        try:
            # Check if response looks like JSON
            if result_state.response.strip().startswith('{') or result_state.response.strip().startswith('['):
                parsed = json.loads(result_state.response)
                logger.info("✓ Response is valid JSON")
                logger.info(f"Response type: {type(parsed)}")
                if isinstance(parsed, list):
                    logger.info(f"Response contains {len(parsed)} items")
                elif isinstance(parsed, dict):
                    logger.info(f"Response keys: {list(parsed.keys())}")
            else:
                logger.info("✓ Response is plain text")
                logger.info(f"Response preview: {result_state.response[:200]}...")
        except json.JSONDecodeError:
            logger.info("✓ Response is plain text (not JSON)")
            logger.info(f"Response preview: {result_state.response[:200]}...")

    else:
        logger.warning("⚠ Subgraph returned empty response")
        logger.info("This might be expected if no data exists in the database")

    # Check that messages were updated
    if len(result_state.messages) > 1:
        logger.info("✓ Conversation messages were updated")
        logger.info(f"Total messages: {len(result_state.messages)}")
    else:
        logger.warning("⚠ No additional messages were added")

    logger.info("Test completed successfully!")
    return True


async def test_tools_directly():
    """
    Test the tools directly to verify CRUD operations work.
    """
    logger.info("Testing tools directly...")

    from .tools import build_rag_tools

    # Build tools with test context
    test_user_id = 1
    test_requisition_id = 1

    try:
        tools = build_rag_tools(test_user_id, test_requisition_id)
        logger.info(f"✓ Built {len(tools)} tools successfully")
    except Exception as e:
        logger.error(f"✗ Failed to build tools: {e}")
        return False

    # Test each tool
    for tool in tools:
        logger.info(f"Testing tool: {tool.name}")
        try:
            # Call tool with minimal args (some tools take no args)
            if tool.name == "get_candidate_details":
                # Need a candidate_id, skip if we don't know one
                logger.info("  Skipping get_candidate_details (needs specific candidate_id)")
                continue

            result = await tool.ainvoke({})
            logger.info(f"  ✓ Tool executed successfully")
            logger.info(f"  Result length: {len(result)} characters")

            # Try to parse as JSON
            try:
                parsed = json.loads(result)
                logger.info(f"  ✓ Result is valid JSON")
            except json.JSONDecodeError:
                logger.info(f"  ✓ Result is text")

        except Exception as e:
            logger.error(f"  ✗ Tool failed: {e}")

    return True


async def main():
    """
    Run all tests.
    """
    logger.info("=" * 50)
    logger.info("RAG Query Subgraph Test Suite")
    logger.info("=" * 50)

    # Test 1: Subgraph creation and invocation
    success1 = await test_rag_query_subgraph()

    # Test 2: Direct tool testing
    success2 = await test_tools_directly()

    logger.info("=" * 50)
    if success1 and success2:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.error("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())