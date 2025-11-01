"""Test that Spellbook discovery returns correct queryable Dune table names."""

import pytest


def test_walrus_table_discovery_returns_dune_table_names():
    """Test that discovering Walrus tables returns correct dune_table field."""
    from spice_mcp.mcp.server import _spellbook_find_models_impl
    
    # Discover walrus models
    result = _spellbook_find_models_impl(
        keyword="walrus",
        schema=None,
        limit=10,
        include_columns=False
    )
    
    assert "models" in result
    walrus_models = result["models"]
    
    # Should find at least the base_table and payments models
    assert len(walrus_models) >= 2
    
    # Check each model has the required fields
    for model in walrus_models:
        assert "dune_schema" in model
        assert "dune_alias" in model
        assert "dune_table" in model
        
        # Verify format is schema.alias (not daily_spellbook.model_name)
        dune_table = model["dune_table"]
        assert "." in dune_table
        assert not dune_table.startswith("daily_spellbook.")
        
        # Verify specific known tables
        if model["table"] == "sui_walrus_base_table":
            assert model["dune_schema"] == "sui_walrus"
            assert model["dune_alias"] == "base_table"
            assert model["dune_table"] == "sui_walrus.base_table"
        elif model["table"] == "sui_walrus_payments":
            assert model["dune_schema"] == "sui_walrus"
            assert model["dune_alias"] == "payments"
            assert model["dune_table"] == "sui_walrus.payments"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

