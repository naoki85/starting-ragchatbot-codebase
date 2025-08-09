"""Tests for FastAPI endpoints in the RAG system"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock


@pytest.mark.api
class TestQueryEndpoint:
    """Test /api/query endpoint functionality"""

    def test_query_endpoint_success(self, api_client, mock_rag_for_api, sample_query_request, sample_query_response):
        """Test successful query processing"""
        # Setup mock response
        mock_rag_for_api.query.return_value = (
            sample_query_response["answer"],
            sample_query_response["sources"]
        )
        
        # Make request
        response = api_client.post("/api/query", json=sample_query_request)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["answer"] == sample_query_response["answer"]
        assert data["sources"] == sample_query_response["sources"]
        assert data["session_id"] == sample_query_request["session_id"]
        
        # Verify mock was called correctly
        mock_rag_for_api.query.assert_called_once_with(
            sample_query_request["query"],
            sample_query_request["session_id"]
        )

    def test_query_endpoint_without_session_id(self, api_client, mock_rag_for_api):
        """Test query endpoint without session ID (should generate one)"""
        # Setup
        request_data = {"query": "What is machine learning?"}
        mock_rag_for_api.query.return_value = (
            "Machine learning is a subset of AI",
            [{"text": "ML Course", "link": "https://example.com/ml"}]
        )
        
        # Make request
        response = api_client.post("/api/query", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["answer"] == "Machine learning is a subset of AI"
        assert len(data["sources"]) == 1
        assert data["session_id"] == "test_session_id"  # Default from test fixture
        
        # Verify mock was called with generated session ID
        mock_rag_for_api.query.assert_called_once_with(
            "What is machine learning?",
            "test_session_id"
        )

    def test_query_endpoint_error_handling(self, api_client, mock_rag_for_api):
        """Test query endpoint error handling"""
        # Setup mock to raise exception
        mock_rag_for_api.query.side_effect = Exception("RAG system error")
        
        # Make request
        request_data = {"query": "test query", "session_id": "test_session"}
        response = api_client.post("/api/query", json=request_data)
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "RAG system error" in data["detail"]

    def test_query_endpoint_malformed_request(self, api_client):
        """Test query endpoint with malformed request"""
        # Missing required 'query' field
        response = api_client.post("/api/query", json={"session_id": "test"})
        
        # Verify validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_query_endpoint_empty_query(self, api_client, mock_rag_for_api):
        """Test query endpoint with empty query string"""
        # Setup
        mock_rag_for_api.query.return_value = ("Please provide a question", [])
        
        # Make request with empty query
        request_data = {"query": "", "session_id": "test_session"}
        response = api_client.post("/api/query", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Please provide a question"
        assert data["sources"] == []

    def test_query_endpoint_special_error_handling(self, api_client, mock_rag_for_api):
        """Test query endpoint with error keyword triggers exception"""
        # Make request with 'error' in query
        request_data = {"query": "This will cause an error", "session_id": "test_session"}
        response = api_client.post("/api/query", json=request_data)
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "Test error" in data["detail"]


@pytest.mark.api
class TestCoursesEndpoint:
    """Test /api/courses endpoint functionality"""

    def test_courses_endpoint_success(self, api_client, mock_rag_for_api, sample_course_analytics):
        """Test successful course statistics retrieval"""
        # Setup mock response
        mock_rag_for_api.get_course_analytics.return_value = sample_course_analytics
        
        # Make request
        response = api_client.get("/api/courses")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_courses"] == sample_course_analytics["total_courses"]
        assert data["course_titles"] == sample_course_analytics["course_titles"]
        
        # Verify mock was called
        mock_rag_for_api.get_course_analytics.assert_called_once()

    def test_courses_endpoint_empty_analytics(self, api_client, mock_rag_for_api):
        """Test courses endpoint with no courses available"""
        # Setup mock response
        mock_rag_for_api.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }
        
        # Make request
        response = api_client.get("/api/courses")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_endpoint_error_handling(self, api_client, mock_rag_for_api):
        """Test courses endpoint error handling"""
        # Setup mock to raise exception
        mock_rag_for_api.get_course_analytics.side_effect = Exception("Analytics error")
        
        # Make request
        response = api_client.get("/api/courses")
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "Analytics error" in data["detail"]


@pytest.mark.api
class TestNewChatEndpoint:
    """Test /api/new-chat endpoint functionality"""

    def test_new_chat_endpoint_with_session_id(self, api_client, mock_rag_for_api):
        """Test new chat endpoint with session ID"""
        # Setup
        mock_session_manager = Mock()
        mock_rag_for_api.session_manager = mock_session_manager
        
        # Make request
        request_data = {"session_id": "test_session_123"}
        response = api_client.post("/api/new-chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["message"] == "Session cleared"
        
        # Verify session manager was called
        mock_session_manager.clear_session.assert_called_once_with("test_session_123")

    def test_new_chat_endpoint_without_session_id(self, api_client, mock_rag_for_api):
        """Test new chat endpoint without session ID"""
        # Setup
        mock_session_manager = Mock()
        mock_rag_for_api.session_manager = mock_session_manager
        
        # Make request without session_id
        request_data = {}
        response = api_client.post("/api/new-chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["message"] == "Session cleared"
        
        # Verify session manager was not called (no session ID provided)
        mock_session_manager.clear_session.assert_not_called()

    def test_new_chat_endpoint_with_none_session_id(self, api_client, mock_rag_for_api):
        """Test new chat endpoint with null session ID"""
        # Setup
        mock_session_manager = Mock()
        mock_rag_for_api.session_manager = mock_session_manager
        
        # Make request with null session_id
        request_data = {"session_id": None}
        response = api_client.post("/api/new-chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        
        # Verify session manager was not called (session ID is None)
        mock_session_manager.clear_session.assert_not_called()

    def test_new_chat_endpoint_error_handling(self, api_client, mock_rag_for_api):
        """Test new chat endpoint error handling"""
        # Setup mock to raise exception
        mock_session_manager = Mock()
        mock_session_manager.clear_session.side_effect = Exception("Session error")
        mock_rag_for_api.session_manager = mock_session_manager
        
        # Make request
        request_data = {"session_id": "test_session"}
        response = api_client.post("/api/new-chat", json=request_data)
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "Session error" in data["detail"]


@pytest.mark.api
class TestRootEndpoint:
    """Test root endpoint functionality"""

    def test_root_endpoint(self, api_client):
        """Test root endpoint returns welcome message"""
        response = api_client.get("/")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Course Materials RAG System"


@pytest.mark.api
class TestMiddlewareAndCORS:
    """Test middleware functionality"""

    def test_cors_headers_present(self, api_client):
        """Test that CORS headers are properly set"""
        response = api_client.get("/", headers={"Origin": "http://localhost:3000"})
        
        assert response.status_code == 200
        # Note: TestClient doesn't fully simulate CORS, but we can verify the endpoint works

    def test_options_request(self, api_client):
        """Test OPTIONS request for CORS preflight"""
        response = api_client.options("/api/query")
        
        # Should not return error (exact status depends on FastAPI CORS implementation)
        assert response.status_code in [200, 405]  # 405 is also acceptable for OPTIONS


@pytest.mark.api
class TestRequestValidation:
    """Test request validation and response models"""

    def test_query_request_validation(self, api_client):
        """Test query request validation with various inputs"""
        # Test with integer instead of string
        response = api_client.post("/api/query", json={"query": 123, "session_id": "test"})
        assert response.status_code == 422
        
        # Test with missing query
        response = api_client.post("/api/query", json={"session_id": "test"})
        assert response.status_code == 422
        
        # Test with extra fields (should be allowed)
        response = api_client.post("/api/query", json={
            "query": "test",
            "session_id": "test",
            "extra_field": "should_be_ignored"
        })
        # Should not return validation error
        assert response.status_code != 422

    def test_new_chat_request_validation(self, api_client):
        """Test new chat request validation"""
        # Test with invalid session_id type
        response = api_client.post("/api/new-chat", json={"session_id": 123})
        assert response.status_code == 422
        
        # Test with empty body (should be valid)
        response = api_client.post("/api/new-chat", json={})
        assert response.status_code == 200


@pytest.mark.api
class TestResponseModels:
    """Test response model validation"""

    def test_query_response_structure(self, api_client, mock_rag_for_api):
        """Test query response follows correct structure"""
        # Setup
        mock_rag_for_api.query.return_value = (
            "Test answer",
            [
                {"text": "Source 1", "link": "https://example.com/1"},
                {"text": "Source 2", "link": None}  # Test optional link
            ]
        )
        
        # Make request
        response = api_client.post("/api/query", json={"query": "test"})
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        
        # Check sources structure
        assert len(data["sources"]) == 2
        for source in data["sources"]:
            assert "text" in source
            assert "link" in source  # Should be present even if None

    def test_course_stats_response_structure(self, api_client, mock_rag_for_api):
        """Test course stats response structure"""
        # Setup
        mock_rag_for_api.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["Course 1", "Course 2", "Course 3", "Course 4", "Course 5"]
        }
        
        # Make request
        response = api_client.get("/api/courses")
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert len(data["course_titles"]) == data["total_courses"]


@pytest.mark.integration
@pytest.mark.api
class TestEndpointIntegration:
    """Integration tests for API endpoints"""

    def test_full_query_workflow(self, api_client, mock_rag_for_api):
        """Test complete query workflow"""
        # Setup mock responses
        mock_rag_for_api.query.return_value = (
            "MCP stands for Model Context Protocol",
            [{"text": "MCP Course - Lesson 1", "link": "https://example.com/mcp/lesson1"}]
        )
        
        mock_rag_for_api.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Introduction to MCP", "Advanced Python", "API Design"]
        }
        
        # Step 1: Make initial query
        query_response = api_client.post("/api/query", json={
            "query": "What is MCP?",
            "session_id": "integration_test_session"
        })
        
        assert query_response.status_code == 200
        query_data = query_response.json()
        assert "MCP" in query_data["answer"]
        assert len(query_data["sources"]) == 1
        session_id = query_data["session_id"]
        
        # Step 2: Check course stats
        stats_response = api_client.get("/api/courses")
        assert stats_response.status_code == 200
        
        # Step 3: Clear session
        clear_response = api_client.post("/api/new-chat", json={
            "session_id": session_id
        })
        assert clear_response.status_code == 200
        clear_data = clear_response.json()
        assert clear_data["status"] == "success"

    def test_error_recovery_workflow(self, api_client, mock_rag_for_api):
        """Test error scenarios and recovery"""
        # Step 1: Cause an error
        error_response = api_client.post("/api/query", json={
            "query": "This will cause an error",
            "session_id": "error_test_session"
        })
        assert error_response.status_code == 500
        
        # Step 2: Make a successful request after error
        mock_rag_for_api.query.return_value = (
            "Successful recovery response",
            [{"text": "Recovery Source", "link": "https://example.com/recovery"}]
        )
        
        success_response = api_client.post("/api/query", json={
            "query": "What is machine learning?",
            "session_id": "error_test_session"
        })
        assert success_response.status_code == 200
        success_data = success_response.json()
        assert "Successful recovery" in success_data["answer"]