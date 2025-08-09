import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
1. **search_course_content**: For searching specific course content and detailed educational materials
2. **get_course_outline**: For getting course structure, lesson lists, and course metadata

Tool Usage Guidelines:
- For **course outline/structure queries** (e.g., "What lessons are in...", "Course overview", "Show me the structure of..."): Use get_course_outline tool
- For **specific content queries** (e.g., detailed questions about concepts, lessons, etc.): Use search_course_content tool
- **Sequential tool usage allowed**: You can use tools multiple times across conversation rounds to gather comprehensive information
- After using a tool and seeing results, you can decide to:
  - Use additional tools if more information is needed
  - Provide a final answer if you have sufficient information
- Consider using get_course_outline first for structure, then search_course_content for details
- **Maximum 2 rounds of tool usage per user query**
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **Sequential reasoning**: Use multiple tool calls when beneficial for comprehensive answers
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
    
    def generate_response_sequential(self, query: str,
                                   conversation_history: Optional[str] = None,
                                   tools: Optional[List] = None,
                                   tool_manager=None,
                                   max_rounds: int = 2) -> str:
        """
        Generate AI response with sequential tool calling capability.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool usage rounds (default: 2)
            
        Returns:
            Generated response as string
        """
        # If no tools available, fall back to standard response
        if not tools or not tool_manager:
            return self.generate_response(query, conversation_history)
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Initialize conversation state
        messages = [{"role": "user", "content": query}]
        round_count = 0
        
        # Continuous conversation loop
        while True:
            # Prepare API call with tools always available
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
                "tools": tools,
                "tool_choice": {"type": "auto"}
            }
            
            try:
                # Get response from Claude
                response = self.client.messages.create(**api_params)
                
                # Check if Claude wants to use tools
                has_tool_use = any(
                    block.type == "tool_use" 
                    for block in response.content
                )
                
                if not has_tool_use:
                    # Natural termination - Claude gave final answer
                    return response.content[0].text
                
                # Claude wants to use tools - check if we've hit the round limit
                round_count += 1
                if round_count > max_rounds:
                    # Max rounds reached - return forced termination
                    return self._handle_forced_termination(response, "max_rounds_reached")
                
                # Execute tools and continue conversation
                tool_execution_success = self._execute_tools_and_update_messages(
                    response, messages, tool_manager
                )
                
                if not tool_execution_success:
                    return self._handle_tool_failure(messages, system_content)
                    
            except Exception as e:
                # API error - return graceful fallback
                return f"I encountered an error while processing your request: {str(e)}"
    
    def _execute_tools_and_update_messages(self, response, messages: List, tool_manager) -> bool:
        """
        Execute tools and update message history for next round.
        
        Returns:
            True if all tools executed successfully, False otherwise
        """
        # Add AI's response to messages
        messages.append({"role": "assistant", "content": response.content})
        
        # Execute all tool calls
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **content_block.input
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
                except Exception as e:
                    # Tool execution failed
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Tool execution failed: {str(e)}"
                    })
                    return False
        
        # Add tool results to conversation
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        return True
    
    def _handle_tool_failure(self, messages: List, system_content: str) -> str:
        """Handle tool execution failures gracefully"""
        try:
            # Try to get a response without tools as fallback
            fallback_params = {
                **self.base_params,
                "messages": messages[:-1],  # Remove failed tool result
                "system": system_content
            }
            fallback_response = self.client.messages.create(**fallback_params)
            return fallback_response.content[0].text
        except:
            return "I encountered an error while processing your request. Please try again."
    
    def _handle_forced_termination(self, response, reason: str) -> str:
        """Handle cases where loop terminates due to limits"""
        if reason == "max_rounds_reached":
            # Extract text response if available
            text_blocks = [block for block in response.content if block.type == "text"]
            if text_blocks:
                return text_blocks[0].text
            return "I've reached the maximum number of tool usage rounds. Please refine your query."
        
        # Default case - return best available response
        return response.content[0].text if response.content else "No response available."