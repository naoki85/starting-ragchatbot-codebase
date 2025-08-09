"""Shared test fixtures and configurations for RAG system tests"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_generator import AIGenerator
from config import Config
from models import Course, CourseChunk, Lesson
from rag_system import RAGSystem
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


@pytest.fixture
def sample_courses():
    """Sample course data for testing"""
    return [
        Course(
            title="Introduction to MCP",
            course_link="https://example.com/mcp-intro",
            instructor="John Doe",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="What is MCP?",
                    lesson_link="https://example.com/mcp-intro/lesson1",
                ),
                Lesson(
                    lesson_number=2,
                    title="MCP Architecture",
                    lesson_link="https://example.com/mcp-intro/lesson2",
                ),
            ],
        ),
        Course(
            title="Advanced Python",
            course_link="https://example.com/python-advanced",
            instructor="Jane Smith",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Decorators",
                    lesson_link="https://example.com/python/lesson1",
                ),
                Lesson(
                    lesson_number=2,
                    title="Metaclasses",
                    lesson_link="https://example.com/python/lesson2",
                ),
            ],
        ),
    ]


@pytest.fixture
def sample_course_chunks():
    """Sample course chunks for testing"""
    return [
        CourseChunk(
            content="MCP (Model Context Protocol) is a standardized way for applications to provide context to AI models.",
            course_title="Introduction to MCP",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="The MCP architecture consists of three main components: hosts, clients, and servers.",
            course_title="Introduction to MCP",
            lesson_number=2,
            chunk_index=1,
        ),
        CourseChunk(
            content="Python decorators are a powerful feature that allows you to modify functions or classes.",
            course_title="Advanced Python",
            lesson_number=1,
            chunk_index=0,
        ),
    ]


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing"""
    mock_store = Mock()

    # Default successful search results
    mock_store.search.return_value = SearchResults(
        documents=[
            "MCP (Model Context Protocol) is a standardized way for applications to provide context to AI models."
        ],
        metadata=[{"course_title": "Introduction to MCP", "lesson_number": 1}],
        distances=[0.2],
        error=None,
    )

    # Default course name resolution
    mock_store._resolve_course_name.return_value = "Introduction to MCP"

    # Default lesson link retrieval
    mock_store.get_lesson_link.return_value = "https://example.com/mcp-intro/lesson1"

    return mock_store


@pytest.fixture
def course_search_tool(mock_vector_store):
    """CourseSearchTool instance with mocked vector store"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    mock_client = Mock()

    # Mock successful response without tool use
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [Mock(text="This is a sample response about MCP.")]
    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_anthropic_client_with_tool_use():
    """Mock Anthropic client that simulates tool use"""
    mock_client = Mock()

    # Mock initial response with tool use
    initial_response = Mock()
    initial_response.stop_reason = "tool_use"

    # Mock tool use content
    tool_use_block = Mock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "search_course_content"
    tool_use_block.id = "tool_123"
    tool_use_block.input = {"query": "What is MCP?"}

    initial_response.content = [tool_use_block]

    # Mock final response after tool execution
    final_response = Mock()
    final_response.stop_reason = "end_turn"
    final_response.content = [
        Mock(text="Based on the course content, MCP stands for Model Context Protocol.")
    ]

    # Configure client to return initial response first, then final response
    mock_client.messages.create.side_effect = [initial_response, final_response]

    return mock_client


@pytest.fixture
def ai_generator_with_mock_client(mock_anthropic_client):
    """AIGenerator with mocked Anthropic client"""
    with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
        mock_anthropic_class.return_value = mock_anthropic_client
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client  # Ensure we use our mock
        return generator


@pytest.fixture
def tool_manager_with_search_tool(course_search_tool):
    """ToolManager with registered CourseSearchTool"""
    manager = ToolManager()
    manager.register_tool(course_search_tool)
    return manager


@pytest.fixture
def test_config():
    """Test configuration"""
    config = Config()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.CHROMA_PATH = "./test_chroma_db"
    config.MAX_RESULTS = 3
    return config


@pytest.fixture
def mock_rag_system(test_config):
    """Mock RAG system for integration testing"""
    with (
        patch("rag_system.DocumentProcessor"),
        patch("rag_system.VectorStore") as mock_vector_store_class,
        patch("rag_system.AIGenerator") as mock_ai_generator_class,
        patch("rag_system.SessionManager") as mock_session_manager_class,
    ):

        # Set up the mock vector store
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        # Set up the mock AI generator
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.return_value = (
            "This is a test response about MCP."
        )
        mock_ai_generator_class.return_value = mock_ai_generator

        # Set up the mock session manager
        mock_session_manager = Mock()
        mock_session_manager.get_conversation_history.return_value = None
        mock_session_manager_class.return_value = mock_session_manager

        # Create RAG system instance
        rag_system = RAGSystem(test_config)

        # Store mocks for test access
        rag_system.mock_vector_store = mock_vector_store
        rag_system.mock_ai_generator = mock_ai_generator
        rag_system.mock_session_manager = mock_session_manager

        # Mock the tool_manager methods that are called in the query method
        rag_system.tool_manager.get_last_sources = Mock(return_value=[])
        rag_system.tool_manager.reset_sources = Mock()
        rag_system.tool_manager.get_tool_definitions = Mock(return_value=[])

        return rag_system


# Search result fixtures for different scenarios
@pytest.fixture
def successful_search_results():
    """Successful search results with multiple matches"""
    return SearchResults(
        documents=[
            "MCP (Model Context Protocol) is a standardized way for applications to provide context to AI models.",
            "The MCP architecture consists of three main components: hosts, clients, and servers.",
        ],
        metadata=[
            {"course_title": "Introduction to MCP", "lesson_number": 1},
            {"course_title": "Introduction to MCP", "lesson_number": 2},
        ],
        distances=[0.2, 0.3],
        error=None,
    )


@pytest.fixture
def empty_search_results():
    """Empty search results"""
    return SearchResults(documents=[], metadata=[], distances=[], error=None)


@pytest.fixture
def error_search_results():
    """Search results with error"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error="Database connection failed"
    )


# API Testing Fixtures
@pytest.fixture
def test_app():
    """Create test FastAPI app without static file mounting to avoid import issues"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional
    
    # Create test app
    app = FastAPI(title="Course Materials RAG System", root_path="")
    
    # Add middleware (same as production)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Define Pydantic models (same as production)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class NewChatRequest(BaseModel):
        session_id: Optional[str] = None

    class SourceItem(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    # Mock RAG system for testing
    mock_rag_system = Mock()
    
    # Define endpoints inline to avoid import issues
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or "test_session_id"
            
            # Mock response based on query
            if "error" in request.query.lower():
                raise Exception("Test error")
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/new-chat")
    async def new_chat(request: NewChatRequest):
        try:
            if request.session_id:
                mock_rag_system.session_manager.clear_session(request.session_id)
            
            return {"status": "success", "message": "Session cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Course Materials RAG System"}
    
    # Store mock for test access
    app.state.mock_rag_system = mock_rag_system
    
    return app


@pytest.fixture
def api_client(test_app):
    """Create test client for API testing"""
    from fastapi.testclient import TestClient
    return TestClient(test_app)


@pytest.fixture
def mock_rag_for_api(test_app):
    """Get the mock RAG system from test app for setup in API tests"""
    return test_app.state.mock_rag_system


@pytest.fixture
def sample_query_request():
    """Sample query request for API testing"""
    return {
        "query": "What is MCP?",
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_query_response():
    """Sample query response for API testing"""
    return {
        "answer": "MCP stands for Model Context Protocol.",
        "sources": [
            {"text": "Introduction to MCP - Lesson 1", "link": "https://example.com/lesson1"}
        ],
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_course_analytics():
    """Sample course analytics for API testing"""
    return {
        "total_courses": 3,
        "course_titles": [
            "Introduction to MCP",
            "Advanced Python",
            "API Design"
        ]
    }
>>>>>>> quality_feature
