"""Tests for RAG system content-query handling"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from rag_system import RAGSystem


class TestRAGSystemQueryHandling:
    """Test RAG system query processing and content handling"""

    def test_query_basic_content_search(self, mock_rag_system):
        """Test basic content search query handling"""
        # Setup
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "MCP stands for Model Context Protocol."
        )
        mock_rag_system.tool_manager.get_last_sources.return_value = [
            {
                "text": "Introduction to MCP - Lesson 1",
                "link": "https://example.com/lesson1",
            }
        ]

        # Execute
        response, sources = mock_rag_system.query("What is MCP?")

        # Verify
        assert response == "MCP stands for Model Context Protocol."
        assert len(sources) == 1
        assert sources[0]["text"] == "Introduction to MCP - Lesson 1"
        assert sources[0]["link"] == "https://example.com/lesson1"

        # Verify AI generator was called with correct parameters
        mock_rag_system.mock_ai_generator.generate_response_sequential.assert_called_once()
        call_args = (
            mock_rag_system.mock_ai_generator.generate_response_sequential.call_args
        )
        assert (
            "Answer this question about course materials: What is MCP?"
            in call_args[1]["query"]
        )
        assert (
            call_args[1]["tools"] == mock_rag_system.tool_manager.get_tool_definitions()
        )
        assert call_args[1]["tool_manager"] == mock_rag_system.tool_manager

    def test_query_with_session_management(self, mock_rag_system):
        """Test query with session ID for conversation history"""
        # Setup
        mock_rag_system.session_manager.get_conversation_history.return_value = (
            "Previous: What is MCP?\nResponse: MCP is..."
        )
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "MCP has three main components."
        )

        # Execute
        response, sources = mock_rag_system.query(
            "Tell me more about MCP components", session_id="test_session"
        )

        # Verify
        assert response == "MCP has three main components."

        # Verify session manager calls
        mock_rag_system.session_manager.get_conversation_history.assert_called_once_with(
            "test_session"
        )
        mock_rag_system.session_manager.add_exchange.assert_called_once_with(
            "test_session",
            "Tell me more about MCP components",
            "MCP has three main components.",
        )

        # Verify history was passed to AI generator
        call_args = (
            mock_rag_system.mock_ai_generator.generate_response_sequential.call_args
        )
        assert (
            call_args[1]["conversation_history"]
            == "Previous: What is MCP?\nResponse: MCP is..."
        )

    def test_query_without_session(self, mock_rag_system):
        """Test query without session ID"""
        # Setup
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "Test response"
        )

        # Execute
        response, sources = mock_rag_system.query("What is machine learning?")

        # Verify
        # Session manager methods should not be called
        mock_rag_system.session_manager.get_conversation_history.assert_not_called()
        mock_rag_system.session_manager.add_exchange.assert_not_called()

        # Verify AI generator called without history
        call_args = (
            mock_rag_system.mock_ai_generator.generate_response_sequential.call_args
        )
        assert call_args[1]["conversation_history"] is None

    def test_query_source_handling_and_reset(self, mock_rag_system):
        """Test proper source handling and reset"""
        # Setup
        test_sources = [
            {"text": "Course A", "link": "https://example.com/a"},
            {"text": "Course B", "link": "https://example.com/b"},
        ]
        mock_rag_system.tool_manager.get_last_sources.return_value = test_sources
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "Test response"
        )

        # Execute
        response, sources = mock_rag_system.query("test query")

        # Verify
        assert sources == test_sources

        # Verify sources were retrieved and reset
        mock_rag_system.tool_manager.get_last_sources.assert_called_once()
        mock_rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_prompt_formatting(self, mock_rag_system):
        """Test that queries are properly formatted for AI"""
        # Setup
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "Test response"
        )

        # Execute
        mock_rag_system.query("What is the difference between MCP and REST APIs?")

        # Verify prompt formatting
        call_args = (
            mock_rag_system.mock_ai_generator.generate_response_sequential.call_args
        )
        expected_prompt = "Answer this question about course materials: What is the difference between MCP and REST APIs?"
        assert call_args[1]["query"] == expected_prompt

    def test_query_tool_definitions_passed(self, mock_rag_system):
        """Test that tool definitions are passed to AI generator"""
        # Setup
        expected_tools = [
            {"name": "search_course_content"},
            {"name": "get_course_outline"},
        ]
        mock_rag_system.tool_manager.get_tool_definitions.return_value = expected_tools
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "Test response"
        )

        # Execute
        mock_rag_system.query("test query")

        # Verify
        call_args = (
            mock_rag_system.mock_ai_generator.generate_response_sequential.call_args
        )
        assert call_args[1]["tools"] == expected_tools

    def test_query_empty_sources(self, mock_rag_system):
        """Test handling when no sources are available"""
        # Setup
        mock_rag_system.tool_manager.get_last_sources.return_value = []
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "General knowledge response"
        )

        # Execute
        response, sources = mock_rag_system.query("What is machine learning?")

        # Verify
        assert response == "General knowledge response"
        assert sources == []


class TestRAGSystemErrorHandling:
    """Test RAG system error handling"""

    def test_query_ai_generator_error(self, mock_rag_system):
        """Test handling of AI generator errors"""
        # Setup
        mock_rag_system.mock_ai_generator.generate_response_sequential.side_effect = (
            Exception("API Error")
        )

        # Execute and verify it raises the exception (or handle gracefully based on implementation)
        with pytest.raises(Exception) as exc_info:
            mock_rag_system.query("What is MCP?")

        assert str(exc_info.value) == "API Error"

    def test_query_session_manager_error(self, mock_rag_system):
        """Test handling of session manager errors"""
        # Setup
        mock_rag_system.session_manager.get_conversation_history.side_effect = (
            Exception("Session Error")
        )
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "Test response"
        )

        # Execute - should handle gracefully or raise
        with pytest.raises(Exception) as exc_info:
            mock_rag_system.query("test query", session_id="test_session")

        assert str(exc_info.value) == "Session Error"

    def test_query_source_handling_error(self, mock_rag_system):
        """Test handling of source retrieval errors"""
        # Setup
        mock_rag_system.tool_manager.get_last_sources.side_effect = Exception(
            "Source Error"
        )
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "Test response"
        )

        # Execute - should handle gracefully or raise
        with pytest.raises(Exception) as exc_info:
            mock_rag_system.query("test query")

        assert str(exc_info.value) == "Source Error"


class TestRAGSystemContentTypes:
    """Test RAG system handling different types of content queries"""

    def test_specific_course_content_query(self, mock_rag_system):
        """Test query about specific course content"""
        # Setup
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "MCP servers handle data processing."
        )
        mock_rag_system.tool_manager.get_last_sources.return_value = [
            {
                "text": "Introduction to MCP - Lesson 2",
                "link": "https://example.com/lesson2",
            }
        ]

        # Execute
        response, sources = mock_rag_system.query("How do MCP servers work?")

        # Verify
        assert "MCP servers handle data processing" in response
        assert len(sources) == 1
        assert "Lesson 2" in sources[0]["text"]

    def test_course_outline_query(self, mock_rag_system):
        """Test query requesting course structure/outline"""
        # Setup - AI should use outline tool for this type of query
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = """**Course Title:** Introduction to MCP
**Instructor:** John Doe
**Lessons (2 total):**
- Lesson 1: What is MCP?
- Lesson 2: MCP Architecture"""

        mock_rag_system.tool_manager.get_last_sources.return_value = [
            {"text": "Introduction to MCP", "link": "https://example.com/mcp-intro"}
        ]

        # Execute
        response, sources = mock_rag_system.query("What lessons are in the MCP course?")

        # Verify
        assert "Course Title" in response
        assert "Lesson 1: What is MCP?" in response
        assert "Lesson 2: MCP Architecture" in response

    def test_general_knowledge_query(self, mock_rag_system):
        """Test general knowledge query that might not need course search"""
        # Setup - AI responds with general knowledge
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = (
            "Machine learning is a subset of AI."
        )
        mock_rag_system.tool_manager.get_last_sources.return_value = (
            []
        )  # No course sources

        # Execute
        response, sources = mock_rag_system.query("What is machine learning?")

        # Verify
        assert response == "Machine learning is a subset of AI."
        assert sources == []

    def test_complex_multi_course_query(self, mock_rag_system):
        """Test complex query that might span multiple courses"""
        # Setup
        mock_rag_system.mock_ai_generator.generate_response_sequential.return_value = "Both MCP and REST APIs are communication protocols, but MCP is specifically designed for AI contexts."
        mock_rag_system.tool_manager.get_last_sources.return_value = [
            {
                "text": "Introduction to MCP - Lesson 1",
                "link": "https://example.com/mcp/lesson1",
            },
            {
                "text": "API Design Course - Lesson 3",
                "link": "https://example.com/api/lesson3",
            },
        ]

        # Execute
        response, sources = mock_rag_system.query("Compare MCP with REST APIs")

        # Verify
        assert "communication protocols" in response
        assert len(sources) == 2
        assert any("MCP" in source["text"] for source in sources)
        assert any("API Design" in source["text"] for source in sources)


class TestRAGSystemIntegration:
    """Test RAG system end-to-end integration"""

    def test_full_workflow_with_real_components(self, test_config):
        """Test full workflow with minimal mocking"""
        # This test uses real components where possible
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_processor,
            patch("rag_system.VectorStore") as mock_vector_store_class,
            patch("rag_system.AIGenerator") as mock_ai_generator_class,
            patch("rag_system.SessionManager") as mock_session_manager_class,
        ):

            # Setup mocks
            mock_vector_store = Mock()
            mock_vector_store_class.return_value = mock_vector_store

            mock_ai_generator = Mock()
            mock_ai_generator.generate_response_sequential.return_value = (
                "Test AI response"
            )
            mock_ai_generator_class.return_value = mock_ai_generator

            mock_session_manager = Mock()
            mock_session_manager.get_conversation_history.return_value = None
            mock_session_manager_class.return_value = mock_session_manager

            # Create RAG system
            rag_system = RAGSystem(test_config)

            # Execute query
            response, sources = rag_system.query(
                "What is MCP?", session_id="test_session"
            )

            # Verify components were initialized
            mock_doc_processor.assert_called_once_with(
                test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP
            )
            mock_vector_store_class.assert_called_once_with(
                test_config.CHROMA_PATH,
                test_config.EMBEDDING_MODEL,
                test_config.MAX_RESULTS,
            )
            mock_ai_generator_class.assert_called_once_with(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Verify tools were registered
            assert len(rag_system.tool_manager.tools) == 2
            assert "search_course_content" in rag_system.tool_manager.tools
            assert "get_course_outline" in rag_system.tool_manager.tools

            # Verify response
            assert response == "Test AI response"

    def test_tool_registration(self, mock_rag_system):
        """Test that tools are properly registered with tool manager"""
        # Verify both tools are registered in the tools dict
        assert len(mock_rag_system.tool_manager.tools) >= 2
        assert "search_course_content" in mock_rag_system.tool_manager.tools
        assert "get_course_outline" in mock_rag_system.tool_manager.tools

    def test_configuration_usage(self, test_config):
        """Test that configuration values are properly used"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_processor,
            patch("rag_system.VectorStore") as mock_vector_store_class,
            patch("rag_system.AIGenerator") as mock_ai_generator_class,
            patch("rag_system.SessionManager") as mock_session_manager_class,
        ):

            # Create RAG system
            RAGSystem(test_config)

            # Verify configuration was used correctly
            mock_doc_processor.assert_called_once_with(
                test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP
            )

            mock_vector_store_class.assert_called_once_with(
                test_config.CHROMA_PATH,
                test_config.EMBEDDING_MODEL,
                test_config.MAX_RESULTS,
            )

            mock_ai_generator_class.assert_called_once_with(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_session_manager_class.assert_called_once_with(test_config.MAX_HISTORY)


class TestRAGSystemAnalytics:
    """Test RAG system analytics functionality"""

    def test_get_course_analytics(self, mock_rag_system):
        """Test course analytics retrieval"""
        # Setup
        mock_rag_system.mock_vector_store.get_course_count.return_value = 5
        mock_rag_system.mock_vector_store.get_existing_course_titles.return_value = [
            "Introduction to MCP",
            "Advanced Python",
            "API Design",
            "Data Structures",
            "Machine Learning",
        ]

        # Execute
        analytics = mock_rag_system.get_course_analytics()

        # Verify
        assert analytics["total_courses"] == 5
        assert len(analytics["course_titles"]) == 5
        assert "Introduction to MCP" in analytics["course_titles"]
        assert "Advanced Python" in analytics["course_titles"]
