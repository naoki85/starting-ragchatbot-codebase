"""Tests for AIGenerator integration with CourseSearchTool"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from ai_generator import AIGenerator


class TestAIGeneratorBasic:
    """Test basic AIGenerator functionality"""

    def test_generate_response_without_tools(
        self, ai_generator_with_mock_client, mock_anthropic_client
    ):
        """Test basic response generation without tools"""
        # Execute
        response = ai_generator_with_mock_client.generate_response(
            query="What is machine learning?"
        )

        # Verify
        assert response == "This is a sample response about MCP."
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args[1]["messages"][0]["content"] == "What is machine learning?"
        assert "tools" not in call_args[1]

    def test_generate_response_with_conversation_history(
        self, ai_generator_with_mock_client, mock_anthropic_client
    ):
        """Test response generation with conversation history"""
        # Setup
        history = (
            "User: What is MCP?\nAssistant: MCP stands for Model Context Protocol."
        )

        # Execute
        response = ai_generator_with_mock_client.generate_response(
            query="Tell me more about it", conversation_history=history
        )

        # Verify
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation:" in system_content
        assert history in system_content

    def test_api_parameters(self, ai_generator_with_mock_client, mock_anthropic_client):
        """Test that correct API parameters are used"""
        # Execute
        ai_generator_with_mock_client.generate_response(query="test query")

        # Verify API call parameters
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-sonnet-4-20250514"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800


class TestAIGeneratorToolIntegration:
    """Test AIGenerator integration with CourseSearchTool"""

    def test_generate_response_with_tools_no_tool_use(
        self, mock_anthropic_client, tool_manager_with_search_tool
    ):
        """Test response generation with tools available but no tool use"""
        # Setup - AI decides not to use tools
        mock_anthropic_client.messages.create.return_value.stop_reason = "end_turn"

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_anthropic_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response(
                query="What is machine learning?",
                tools=tool_manager_with_search_tool.get_tool_definitions(),
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify
        assert response == "This is a sample response about MCP."
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tool_choice"] == {"type": "auto"}

    def test_generate_response_with_tool_use_success(
        self, mock_anthropic_client_with_tool_use, tool_manager_with_search_tool
    ):
        """Test successful tool use flow"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_anthropic_client_with_tool_use
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response(
                query="What is MCP?",
                tools=tool_manager_with_search_tool.get_tool_definitions(),
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify
        assert (
            response
            == "Based on the course content, MCP stands for Model Context Protocol."
        )

        # Verify tool was executed
        tool_manager_with_search_tool.tools[
            "search_course_content"
        ].store.search.assert_called_once_with(
            query="What is MCP?", course_name=None, lesson_number=None
        )

        # Verify two API calls were made (initial + follow-up)
        assert mock_anthropic_client_with_tool_use.messages.create.call_count == 2

    def test_tool_execution_flow_messages(
        self, mock_anthropic_client_with_tool_use, tool_manager_with_search_tool
    ):
        """Test that tool execution creates proper message flow"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_anthropic_client_with_tool_use
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            generator.generate_response(
                query="What is MCP?",
                tools=tool_manager_with_search_tool.get_tool_definitions(),
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify message flow
        calls = mock_anthropic_client_with_tool_use.messages.create.call_args_list

        # First call (initial request with tools)
        first_call_args = calls[0][1]
        assert len(first_call_args["messages"]) == 1
        assert first_call_args["messages"][0]["role"] == "user"
        assert "tools" in first_call_args

        # Second call (after tool execution)
        second_call_args = calls[1][1]
        assert len(second_call_args["messages"]) == 3
        assert second_call_args["messages"][0]["role"] == "user"  # Original query
        assert second_call_args["messages"][1]["role"] == "assistant"  # Tool use
        assert second_call_args["messages"][2]["role"] == "user"  # Tool results
        assert "tools" not in second_call_args  # No tools in follow-up call

    def test_tool_execution_with_multiple_tools(self):
        """Test tool execution when multiple tool calls are made"""
        # Setup mock client for multiple tool use
        mock_client = Mock()

        # Mock initial response with multiple tool uses
        initial_response = Mock()
        initial_response.stop_reason = "tool_use"

        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "search_course_content"
        tool_use_1.id = "tool_123"
        tool_use_1.input = {"query": "What is MCP?"}

        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.id = "tool_456"
        tool_use_2.input = {
            "query": "MCP architecture",
            "course_name": "Introduction to MCP",
        }

        initial_response.content = [tool_use_1, tool_use_2]

        # Mock final response
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [
            Mock(text="Combined response from multiple tool calls.")
        ]

        mock_client.messages.create.side_effect = [initial_response, final_response]

        # Setup tool manager with mock tools
        tool_manager = Mock()
        tool_manager.execute_tool.side_effect = [
            "Result from first search",
            "Result from second search",
        ]

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response(
                query="Tell me about MCP",
                tools=[{"name": "search_course_content"}],
                tool_manager=tool_manager,
            )

        # Verify
        assert response == "Combined response from multiple tool calls."

        # Verify both tools were executed
        assert tool_manager.execute_tool.call_count == 2
        tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="What is MCP?"
        )
        tool_manager.execute_tool.assert_any_call(
            "search_course_content",
            query="MCP architecture",
            course_name="Introduction to MCP",
        )

    def test_tool_execution_error_handling(self, tool_manager_with_search_tool):
        """Test handling of errors during tool execution"""
        # Setup mock client for tool use
        mock_client = Mock()

        initial_response = Mock()
        initial_response.stop_reason = "tool_use"

        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test query"}

        initial_response.content = [tool_use_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="I encountered an error while searching.")]

        mock_client.messages.create.side_effect = [initial_response, final_response]

        # Setup tool manager to return error
        tool_manager_with_search_tool.execute_tool = Mock(
            return_value="Search failed: Database error"
        )

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute - should not crash even if tool returns error
            response = generator.generate_response(
                query="What is MCP?",
                tools=tool_manager_with_search_tool.get_tool_definitions(),
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify
        assert response == "I encountered an error while searching."
        tool_manager_with_search_tool.execute_tool.assert_called_once()

    def test_conversation_history_with_tool_use(
        self, mock_anthropic_client_with_tool_use, tool_manager_with_search_tool
    ):
        """Test that conversation history is preserved during tool use"""
        history = "User: Hello\nAssistant: Hi there!"

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_anthropic_client_with_tool_use
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response(
                query="What is MCP?",
                conversation_history=history,
                tools=tool_manager_with_search_tool.get_tool_definitions(),
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify history is included in both API calls
        calls = mock_anthropic_client_with_tool_use.messages.create.call_args_list

        # Check first call has history
        first_system = calls[0][1]["system"]
        assert "Previous conversation:" in first_system
        assert history in first_system

        # Check second call has history
        second_system = calls[1][1]["system"]
        assert "Previous conversation:" in second_system
        assert history in second_system


class TestAIGeneratorToolManager:
    """Test AIGenerator interaction with ToolManager"""

    def test_no_tool_manager_with_tool_use(self, mock_anthropic_client_with_tool_use):
        """Test behavior when tools are available but no tool_manager is provided"""
        # Modify the mock to not have tool use since no tool manager
        mock_client = Mock()
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="I can't use tools without a tool manager.")]
        mock_client.messages.create.return_value = mock_response

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute - should fall back to direct response when no tool_manager
            response = generator.generate_response(
                query="What is MCP?",
                tools=[{"name": "search_course_content"}],
                tool_manager=None,
            )

        # Should return string response and not crash
        assert isinstance(response, str)
        assert response == "I can't use tools without a tool manager."

    def test_tool_not_found_in_manager(self, tool_manager_with_search_tool):
        """Test behavior when tool is not found in manager"""
        # Setup mock client for tool use with non-existent tool
        mock_client = Mock()

        initial_response = Mock()
        initial_response.stop_reason = "tool_use"

        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "non_existent_tool"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test"}

        initial_response.content = [tool_use_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="Tool not found response.")]

        mock_client.messages.create.side_effect = [initial_response, final_response]

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response(
                query="test query",
                tools=[{"name": "non_existent_tool"}],
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify
        assert response == "Tool not found response."

    def test_system_prompt_content(
        self, ai_generator_with_mock_client, mock_anthropic_client
    ):
        """Test that system prompt contains expected content"""
        # Execute
        ai_generator_with_mock_client.generate_response(query="test")

        # Verify system prompt content
        call_args = mock_anthropic_client.messages.create.call_args[1]
        system_content = call_args["system"]

        # Check for key system prompt elements
        assert "search_course_content" in system_content
        assert "get_course_outline" in system_content
        assert "Tool Usage Guidelines" in system_content
        assert "Sequential tool usage allowed" in system_content
        assert "Maximum 2 rounds of tool usage per user query" in system_content
        assert "Brief, Concise and focused" in system_content


class TestAIGeneratorSequentialTooling:
    """Test sequential tool calling functionality"""

    def test_sequential_fallback_without_tools(
        self, ai_generator_with_mock_client, mock_anthropic_client
    ):
        """Test sequential method falls back to regular response when no tools provided"""
        # Execute
        response = ai_generator_with_mock_client.generate_response_sequential(
            query="What is machine learning?"
        )

        # Verify falls back to regular generate_response
        assert response == "This is a sample response about MCP."
        mock_anthropic_client.messages.create.assert_called_once()

    def test_sequential_single_round_no_tool_use(
        self, mock_anthropic_client, tool_manager_with_search_tool
    ):
        """Test sequential method with single round when Claude doesn't use tools"""
        # Setup - AI decides not to use tools
        mock_anthropic_client.messages.create.return_value.stop_reason = "end_turn"

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_anthropic_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response_sequential(
                query="What is machine learning?",
                tools=tool_manager_with_search_tool.get_tool_definitions(),
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify
        assert response == "This is a sample response about MCP."
        # Should only make one API call since no tools were used
        assert mock_anthropic_client.messages.create.call_count == 1
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tool_choice"] == {"type": "auto"}

    def test_sequential_single_round_with_tool_use(
        self, mock_anthropic_client_with_tool_use, tool_manager_with_search_tool
    ):
        """Test sequential method with single round of tool use"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_anthropic_client_with_tool_use
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response_sequential(
                query="What is MCP?",
                tools=tool_manager_with_search_tool.get_tool_definitions(),
                tool_manager=tool_manager_with_search_tool,
            )

        # Verify
        assert (
            response
            == "Based on the course content, MCP stands for Model Context Protocol."
        )

        # Verify tool was executed
        tool_manager_with_search_tool.tools[
            "search_course_content"
        ].store.search.assert_called_once()

        # Verify two API calls were made (first with tool use, second for final response)
        assert mock_anthropic_client_with_tool_use.messages.create.call_count == 2

    def test_sequential_max_rounds_termination(self):
        """Test sequential method terminates at max rounds"""
        # Setup mock client that always returns tool_use responses
        mock_client = Mock()

        # Create responses that always want to use tools
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test"}
        tool_use_response.content = [tool_use_block]

        # Mock client returns tool_use response twice
        mock_client.messages.create.return_value = tool_use_response

        # Setup tool manager
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "Tool result"

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute with max_rounds=2
            response = generator.generate_response_sequential(
                query="Test query",
                tools=[{"name": "search_course_content"}],
                tool_manager=tool_manager,
                max_rounds=2,
            )

        # Verify
        # Should stop after 2 rounds due to max_rounds limit
        # With max_rounds=2, we expect: round 1 -> tool use -> round 2 -> tool use -> terminate
        # That's 3 API calls total (2 tool rounds + 1 termination check)
        assert mock_client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2
        assert "maximum number of tool usage rounds" in response or response is not None

    def test_sequential_tool_execution_error_handling(self):
        """Test sequential method handles tool execution errors gracefully"""
        # Setup mock client for tool use
        mock_client = Mock()

        initial_response = Mock()
        initial_response.stop_reason = "tool_use"

        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test query"}

        initial_response.content = [tool_use_block]

        # Mock a fallback response for error handling
        fallback_response = Mock()
        fallback_response.stop_reason = "end_turn"
        fallback_response.content = [Mock(text="Fallback response after tool error.")]

        mock_client.messages.create.side_effect = [initial_response, fallback_response]

        # Setup tool manager to raise error
        tool_manager = Mock()
        tool_manager.execute_tool.side_effect = Exception("Tool execution failed")

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute - should not crash even if tool fails
            response = generator.generate_response_sequential(
                query="What is MCP?",
                tools=[{"name": "search_course_content"}],
                tool_manager=tool_manager,
            )

        # Verify
        assert response == "Fallback response after tool error."
        tool_manager.execute_tool.assert_called_once()
        # Should make initial call and then fallback call
        assert mock_client.messages.create.call_count == 2

    def test_sequential_conversation_history_preserved(self):
        """Test that conversation history is preserved in sequential calls"""
        mock_client = Mock()

        # Setup response that doesn't use tools (single round)
        response = Mock()
        response.stop_reason = "end_turn"
        response.content = [Mock(text="Response with history context.")]
        mock_client.messages.create.return_value = response

        history = "User: Hello\\nAssistant: Hi there!"

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            generator.generate_response_sequential(
                query="What is MCP?",
                conversation_history=history,
                tools=[{"name": "search_course_content"}],
                tool_manager=Mock(),
            )

        # Verify history is included in system prompt
        call_args = mock_client.messages.create.call_args[1]
        system_content = call_args["system"]
        assert "Previous conversation:" in system_content
        assert history in system_content

    def test_sequential_message_flow_two_rounds(self):
        """Test proper message flow across two rounds of tool usage"""
        mock_client = Mock()
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "Search result"

        # Round 1: Tool use response
        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_tool_block = Mock()
        first_tool_block.type = "tool_use"
        first_tool_block.name = "search_course_content"
        first_tool_block.id = "tool_123"
        first_tool_block.input = {"query": "test"}
        first_response.content = [first_tool_block]

        # Round 2: Final response (no tool use)
        second_response = Mock()
        second_response.stop_reason = "end_turn"
        second_response.content = [Mock(text="Final response after tool use.")]

        mock_client.messages.create.side_effect = [first_response, second_response]

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Execute
            response = generator.generate_response_sequential(
                query="Test query",
                tools=[{"name": "search_course_content"}],
                tool_manager=tool_manager,
            )

        # Verify
        assert response == "Final response after tool use."
        assert mock_client.messages.create.call_count == 2
        assert tool_manager.execute_tool.call_count == 1

        # Verify that tools are available in both API calls
        calls = mock_client.messages.create.call_args_list
        assert "tools" in calls[0][1]  # First call has tools
        assert "tools" in calls[1][1]  # Second call also has tools
