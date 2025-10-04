"""Test data fetcher functionality"""

def test_data_fetcher_engine_import():
    """Test that data fetcher engine can be imported"""
    from mcp.data_fetcher_engine import get_prefetch_data, get_available_fetchers
    assert callable(get_prefetch_data)
    assert callable(get_available_fetchers)

def test_data_fetcher_schemas():
    """Test that data fetcher schemas work"""
    from mcp.schemas import DataFetcherCreate, DataFetcherOut
    
    # Test creating a data fetcher schema
    fetcher_data = {
        "fetcher_key": "test_fetcher",
        "description": "Test fetcher description", 
        "ttl_seconds": 300,
        "python_code": "result = {'test': True}",
        "is_active": True
    }
    
    fetcher = DataFetcherCreate(**fetcher_data)
    assert fetcher.fetcher_key == "test_fetcher"
    assert fetcher.ttl_seconds == 300
    assert fetcher.is_active == True