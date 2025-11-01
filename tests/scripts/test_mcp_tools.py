#!/usr/bin/env python3
"""
Test script to verify MCP tool functionality.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src path to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from spice_mcp.config import Config
from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
from spice_mcp.service_layer.query_service import QueryService
from spice_mcp.logging.query_history import QueryHistory


async def test_mcp_tools():
    """Test MCP tool interface."""
    print("🔧 Testing MCP Tools functionality...")
    
    # Load configuration and API key
    api_key = os.getenv("DUNE_API_KEY")
    if not api_key:
        print("❌ DUNE_API_KEY not found in environment")
        return False
    
    # Create configuration
    from spice_mcp.config import DuneConfig
    config = Config(
        dune=DuneConfig(api_key=api_key)
    )
    
    # Create services
    from pathlib import Path
    
    query_service = QueryService(config)
    
    # Create query history with appropriate paths
    history_path = Path("/tmp") / "spice_test_history.jsonl"
    artifact_root = Path("/tmp") / "spice_test_artifacts"
    query_history = QueryHistory(history_path, artifact_root)
    
    # Create tool
    execute_tool = ExecuteQueryTool(config, query_service, query_history)
    
    print(f"✓ Tool created: {execute_tool.name}")
    print(f"✓ Description: {execute_tool.description}")
    
    test_cases = []
    
    # Test 1: Simple query execution through tool interface
    print("\n📊 Test 1: Execute query through MCP tool")
    try:
        result = await execute_tool.execute(
            query="SELECT 1 as test_col, 'mcp_test' as message",
            performance="medium"
        )
        
        print(f"✓ Tool execution successful")
        print(f"✓ Result type: {type(result)}")
        print(f"✓ Keys in result: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict) and 'preview' in result:
            preview = result['preview']
            if isinstance(preview, dict) and 'rowcount' in preview:
                print(f"✓ Row count: {preview['rowcount']}")
        
        test_cases.append(("Simple query execution", True))
        
    except Exception as e:
        print(f"❌ Tool execution failed: {e}")
        test_cases.append(("Simple query execution", False))
    
    # Test 2: Query with parameters through tool
    print("\n🔧 Test 2: Execute parameterized query through MCP tool")
    try:
        result = await execute_tool.execute(
            query="SELECT '{{test_param}}' as param_value, 42 as number",
            parameters={"test_param": "hello_world"},
            performance="medium"
        )
        
        print(f"✓ Parameterized tool execution successful")
        
        test_cases.append(("Parameterized query execution", True))
        
    except Exception as e:
        print(f"❌ Parameterized tool execution failed: {e}")
        test_cases.append(("Parameterized query execution", False))
    
    # Test 3: Test parameter schema
    print("\n📋 Test 3: Get tool parameter schema")
    try:
        schema = execute_tool.get_parameter_schema()
        print(f"✓ Schema retrieved successfully")
        print(f"✓ Schema type: {schema.get('type', 'Unknown')}")
        if 'properties' in schema:
            print(f"✓ Available properties: {list(schema['properties'].keys())}")
        
        test_cases.append(("Parameter schema", True))
        
    except Exception as e:
        print(f"❌ Schema retrieval failed: {e}")
        test_cases.append(("Parameter schema", False))
    
    # Summary
    print("\n📋 Test Summary:")
    passed = sum(1 for _, success in test_cases if success)
    total = len(test_cases)
    print(f"✅ {passed}/{total} tests passed")
    
    for test_name, success in test_cases:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
    
    return passed == total


if __name__ == "__main__":
    # Set environment variables
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
    
    success = asyncio.run(test_mcp_tools())
    sys.exit(0 if success else 1)
