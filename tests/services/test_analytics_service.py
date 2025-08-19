# tests/services/test_analytics_service.py
import pytest
import networkx as nx

from pydepgraph.services.analytics_service import GraphAnalyticsService
from pydepgraph.database import GraphDatabase

@pytest.fixture
def mock_db_for_analytics(mocker):
    """Mocks the GraphDatabase to return a pre-defined graph."""
    mock_db = mocker.Mock(spec=GraphDatabase)

    # Create a sample graph for testing
    G = nx.DiGraph()
    G.add_edges_from([
        ("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("E", "C")
    ])
    # Expected Fan-in: A:0, B:1, C:2, D:2, E:0
    # Expected Fan-out: A:2, B:1, C:1, D:0, E:1

    mocker.patch.object(GraphAnalyticsService, "_build_graph", return_value=G)

    return mock_db

def test_calculate_fan_in_out(mock_db_for_analytics):
    """
    Tests the calculation of fan-in and fan-out metrics.
    """
    service = GraphAnalyticsService(mock_db_for_analytics)

    fan_in, fan_out = service.calculate_fan_in_out()

    expected_fan_in = {"A": 0, "B": 1, "C": 2, "D": 2, "E": 0}
    expected_fan_out = {"A": 2, "B": 1, "C": 1, "D": 0, "E": 1}

    assert fan_in == expected_fan_in
    assert fan_out == expected_fan_out

def test_calculate_centrality_measures(mock_db_for_analytics):
    """
    Tests the calculation of centrality measures against networkx itself.
    """
    service = GraphAnalyticsService(mock_db_for_analytics)
    graph = service._build_graph() # The mock graph from the fixture

    # Test Betweenness Centrality
    betweenness = service.calculate_betweenness_centrality()
    expected_betweenness = nx.betweenness_centrality(graph)
    assert betweenness.keys() == expected_betweenness.keys()
    for node in betweenness:
        assert betweenness[node] == pytest.approx(expected_betweenness[node])

    # Test Closeness Centrality
    closeness = service.calculate_closeness_centrality()
    expected_closeness = nx.closeness_centrality(graph)
    assert closeness.keys() == expected_closeness.keys()
    for node in closeness:
        assert closeness[node] == pytest.approx(expected_closeness[node])

def test_get_all_metrics(mock_db_for_analytics):
    """
    Tests the consolidated `get_all_metrics` method by comparing
    its output to the individual metric calculation methods.
    """
    service = GraphAnalyticsService(mock_db_for_analytics)

    metrics = service.get_all_metrics()

    assert isinstance(metrics, list)
    assert len(metrics) == 5 # A, B, C, D, E

    metrics_map = {item['node']: item for item in metrics}

    # Get results from individual methods to compare against
    fan_in, fan_out = service.calculate_fan_in_out()
    betweenness = service.calculate_betweenness_centrality()
    closeness = service.calculate_closeness_centrality()

    # Check for a sample node 'A'
    node_a = metrics_map['A']
    assert node_a['fan_in'] == fan_in['A']
    assert node_a['fan_out'] == fan_out['A']
    assert node_a['betweenness'] == pytest.approx(betweenness['A'])
    assert node_a['closeness'] == pytest.approx(closeness['A'])

    # Check for a sample node 'C'
    node_c = metrics_map['C']
    assert node_c['fan_in'] == fan_in['C']
    assert node_c['fan_out'] == fan_out['C']
    assert node_c['betweenness'] == pytest.approx(betweenness['C'])
    assert node_c['closeness'] == pytest.approx(closeness['C'])
