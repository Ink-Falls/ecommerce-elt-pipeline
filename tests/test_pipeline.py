import pytest
import requests
from pydantic import BaseModel, Field, PositiveFloat
from src.pipeline import fetch_api_data


# --- 1. DATA CONTRACT SPECIFICATION ---
class ProductContract(BaseModel):
    id: int
    title: str
    price: PositiveFloat = Field(..., description="Price must be positive")
    category: str


# --- 2. TESTS ---
def test_product_data_contract():
    """Verify that a sample API response strictly adheres to our schema contract."""
    sample_payload = {
        "id": 1,
        "title": "Fjallraven Backpack",
        "price": 109.95,
        "category": "men's clothing",
    }
    
    # Validates payload against the contract
    validated_product = ProductContract(**sample_payload)
    assert validated_product.id == 1
    assert validated_product.price > 0


def test_api_network_failure(requests_mock):
    """Verify that the pipeline cleanly raises an HTTPError on API 500 failure."""
    # Simulate the API failing with an HTTP 500 Internal Server Error
    requests_mock.get("https://fakestoreapi.com/products", status_code=500)

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_api_data("products")