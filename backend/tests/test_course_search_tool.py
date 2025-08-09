"""Tests for CourseSearchTool execute method outputs"""

from unittest.mock import Mock, patch

import pytest
from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test suite for CourseSearchTool.execute() method"""

    def test_execute_query_only_success(
        self, course_search_tool, mock_vector_store, successful_search_results
    ):
        """Test execute with query only - successful results"""
        # Setup
        mock_vector_store.search.return_value = successful_search_results

        # Execute
        result = course_search_tool.execute(query="What is MCP?")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name=None, lesson_number=None
        )
        assert "[Introduction to MCP - Lesson 1]" in result
        assert "[Introduction to MCP - Lesson 2]" in result
        assert "MCP (Model Context Protocol)" in result
        assert "three main components" in result

    def test_execute_with_course_name_success(
        self, course_search_tool, mock_vector_store, successful_search_results
    ):
        """Test execute with course name filter - successful results"""
        # Setup
        mock_vector_store.search.return_value = successful_search_results

        # Execute
        result = course_search_tool.execute(query="What is MCP?", course_name="MCP")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name="MCP", lesson_number=None
        )
        assert "[Introduction to MCP - Lesson 1]" in result
        assert "MCP (Model Context Protocol)" in result

    def test_execute_with_lesson_number_success(
        self, course_search_tool, mock_vector_store, successful_search_results
    ):
        """Test execute with lesson number filter - successful results"""
        # Setup
        mock_vector_store.search.return_value = successful_search_results

        # Execute
        result = course_search_tool.execute(query="What is MCP?", lesson_number=1)

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name=None, lesson_number=1
        )
        assert "[Introduction to MCP - Lesson 1]" in result

    def test_execute_with_both_filters_success(
        self, course_search_tool, mock_vector_store, successful_search_results
    ):
        """Test execute with both course name and lesson number filters"""
        # Setup
        mock_vector_store.search.return_value = successful_search_results

        # Execute
        result = course_search_tool.execute(
            query="What is MCP?", course_name="Introduction to MCP", lesson_number=1
        )

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name="Introduction to MCP", lesson_number=1
        )
        assert "[Introduction to MCP - Lesson 1]" in result

    def test_execute_empty_results_no_filters(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute with empty results and no filters"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results

        # Execute
        result = course_search_tool.execute(query="non-existent topic")

        # Verify
        assert result == "No relevant content found."

    def test_execute_empty_results_with_course_filter(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute with empty results and course filter"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results

        # Execute
        result = course_search_tool.execute(
            query="non-existent topic", course_name="Test Course"
        )

        # Verify
        assert result == "No relevant content found in course 'Test Course'."

    def test_execute_empty_results_with_lesson_filter(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute with empty results and lesson filter"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results

        # Execute
        result = course_search_tool.execute(query="non-existent topic", lesson_number=5)

        # Verify
        assert result == "No relevant content found in lesson 5."

    def test_execute_empty_results_with_both_filters(
        self, course_search_tool, mock_vector_store, empty_search_results
    ):
        """Test execute with empty results and both filters"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results

        # Execute
        result = course_search_tool.execute(
            query="non-existent topic", course_name="Test Course", lesson_number=5
        )

        # Verify
        assert (
            result == "No relevant content found in course 'Test Course' in lesson 5."
        )

    def test_execute_search_error(
        self, course_search_tool, mock_vector_store, error_search_results
    ):
        """Test execute when search returns an error"""
        # Setup
        mock_vector_store.search.return_value = error_search_results

        # Execute
        result = course_search_tool.execute(query="What is MCP?")

        # Verify
        assert result == "Database connection failed"

    def test_execute_result_formatting(self, course_search_tool, mock_vector_store):
        """Test proper formatting of search results"""
        # Setup - custom search results for formatting test
        search_results = SearchResults(
            documents=[
                "First piece of content about MCP.",
                "Second piece of content about architecture.",
            ],
            metadata=[
                {"course_title": "Introduction to MCP", "lesson_number": 1},
                {"course_title": "Introduction to MCP", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
            error=None,
        )
        mock_vector_store.search.return_value = search_results

        # Execute
        result = course_search_tool.execute(query="test query")

        # Verify formatting
        lines = result.split("\n\n")
        assert len(lines) == 2  # Two results separated by double newlines
        assert lines[0].startswith("[Introduction to MCP - Lesson 1]")
        assert lines[1].startswith("[Introduction to MCP - Lesson 2]")
        assert "First piece of content about MCP." in lines[0]
        assert "Second piece of content about architecture." in lines[1]

    def test_execute_source_tracking_with_lesson_links(
        self, course_search_tool, mock_vector_store
    ):
        """Test that sources are properly tracked with lesson links"""
        # Setup
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Introduction to MCP", "lesson_number": 1}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Execute
        course_search_tool.execute(query="test query")

        # Verify sources are tracked
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source["text"] == "Introduction to MCP - Lesson 1"
        assert source["link"] == "https://example.com/lesson1"

    def test_execute_source_tracking_without_lesson_links(
        self, course_search_tool, mock_vector_store
    ):
        """Test that sources are properly tracked without lesson links"""
        # Setup
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Introduction to MCP", "lesson_number": None}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = search_results

        # Execute
        course_search_tool.execute(query="test query")

        # Verify sources are tracked
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source["text"] == "Introduction to MCP"
        assert source["link"] is None

    def test_execute_source_tracking_error_handling(
        self, course_search_tool, mock_vector_store
    ):
        """Test that source tracking handles errors gracefully"""
        # Setup
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Introduction to MCP", "lesson_number": 1}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = search_results
        mock_vector_store.get_lesson_link.side_effect = Exception(
            "Link retrieval failed"
        )

        # Execute - should not crash even if lesson link retrieval fails
        result = course_search_tool.execute(query="test query")

        # Verify it still works and source is tracked without link
        assert "[Introduction to MCP - Lesson 1]" in result
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source["text"] == "Introduction to MCP - Lesson 1"
        assert source["link"] is None

    def test_execute_unknown_course_metadata(
        self, course_search_tool, mock_vector_store
    ):
        """Test handling of results with unknown course metadata"""
        # Setup
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "unknown", "lesson_number": None}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = search_results

        # Execute
        result = course_search_tool.execute(query="test query")

        # Verify
        assert "[unknown]" in result
        assert len(course_search_tool.last_sources) == 1
        assert course_search_tool.last_sources[0]["text"] == "unknown"

    def test_execute_multiple_results_source_tracking(
        self, course_search_tool, mock_vector_store
    ):
        """Test source tracking with multiple results"""
        # Setup
        search_results = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
            error=None,
        )
        mock_vector_store.search.return_value = search_results
        mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/a/lesson1",
            "https://example.com/b/lesson2",
        ]

        # Execute
        result = course_search_tool.execute(query="test query")

        # Verify multiple sources are tracked
        assert len(course_search_tool.last_sources) == 2
        assert course_search_tool.last_sources[0]["text"] == "Course A - Lesson 1"
        assert (
            course_search_tool.last_sources[0]["link"]
            == "https://example.com/a/lesson1"
        )
        assert course_search_tool.last_sources[1]["text"] == "Course B - Lesson 2"
        assert (
            course_search_tool.last_sources[1]["link"]
            == "https://example.com/b/lesson2"
        )


class TestCourseSearchToolToolDefinition:
    """Test CourseSearchTool tool definition"""

    def test_get_tool_definition(self, course_search_tool):
        """Test that tool definition is correctly structured"""
        definition = course_search_tool.get_tool_definition()

        # Verify structure
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition

        # Verify schema
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]
        assert schema["required"] == ["query"]

    def test_tool_definition_parameter_types(self, course_search_tool):
        """Test that tool definition parameter types are correct"""
        definition = course_search_tool.get_tool_definition()
        properties = definition["input_schema"]["properties"]

        assert properties["query"]["type"] == "string"
        assert properties["course_name"]["type"] == "string"
        assert properties["lesson_number"]["type"] == "integer"
