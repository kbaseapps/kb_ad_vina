import pytest
from operator import attrgetter

def pytest_collection_modifyitems(items):
    """Modifies test items in place to ensure test modules run in a given order."""
    items.sort(key=attrgetter("name"))
