# RAG System Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                            User Interface                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ Chat Input  │  │ Send Button │  │   Messages  │  │   Loading Animation │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                                   1. sendMessage()                                 │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                        JavaScript Handler                                    │   │
│  │  • Disable input/button                                                     │   │
│  │  • Add loading animation                                                    │   │
│  │  • Prepare HTTP request                                                     │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                2. HTTP POST /api/query
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 BACKEND                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Route Handler                                │   │
│  │  POST /api/query                                                            │   │
│  │  • Validate QueryRequest model                                              │   │
│  │  • Create session if needed                                                 │   │
│  │  • Call RAG system                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                                3. rag_system.query()                               │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                         RAG System Orchestrator                             │   │
│  │  • Prepare educational prompt                                               │   │
│  │  • Get conversation history                                                 │   │
│  │  • Setup course search tool                                                 │   │
│  │  • Call AI generator                                                        │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                             4. ai_generator.generate_response()                     │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                           AI Generator                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                  Anthropic Claude API Call                             │  │   │
│  │  │  • System prompt for course materials                                  │  │   │
│  │  │  • User query + conversation history                                   │  │   │
│  │  │  • Available tools: CourseSearchTool                                   │  │   │
│  │  │  • Temperature=0, max_tokens=800                                       │  │   │
│  │  └────────────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                          5. Claude decides: "Need to search?"                      │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                       Course Search Tool                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │              Tool Execution (if needed)                                │  │   │
│  │  │  • Tool: "search_course_content"                                       │  │   │
│  │  │  • Smart course name matching                                          │  │   │
│  │  │  • Query vector embedding                                              │  │   │
│  │  └────────────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                                6. vector_store.search()                            │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                          Vector Store                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                        ChromaDB                                        │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │   │
│  │  │  │   Embedding  │  │  Similarity  │  │   Return     │                │  │   │
│  │  │  │  Generation  │→ │    Search    │→ │   Results    │                │  │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘                │  │   │
│  │  │  • sentence-transformers            • Top 5 chunks                   │  │   │
│  │  │  • all-MiniLM-L6-v2                 • Metadata included               │  │   │
│  │  └────────────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                              7. Return search results                              │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                    Claude Response Synthesis                                 │   │
│  │  • Combine search results with knowledge                                    │   │
│  │  • Use conversation history for context                                     │   │
│  │  • Generate educational response                                            │   │
│  │  • Track source documents                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                               8. Return to FastAPI                                 │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                         API Response                                        │   │
│  │  {                                                                          │   │
│  │    "answer": "AI-generated response",                                       │   │
│  │    "sources": ["course chunk sources"],                                     │   │
│  │    "session_id": "session_identifier"                                       │   │
│  │  }                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                9. HTTP 200 Response
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND RESPONSE HANDLING                              │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                       JavaScript Response Handler                           │   │
│  │  • Remove loading animation                                                 │   │
│  │  • Parse JSON response                                                      │   │
│  │  • Convert markdown to HTML                                                 │   │
│  │  • Display message with sources                                             │   │
│  │  • Update session ID                                                        │   │
│  │  • Re-enable input/button                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│                               10. Update UI                                        │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                          Updated Chat Interface                             │   │
│  │  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────────────────┐  │   │
│  │  │ User Query  │  │  AI Response     │  │      Collapsible Sources       │  │   │
│  │  │ (escaped)   │  │  (markdown→HTML) │  │      (course chunk refs)       │  │   │
│  │  └─────────────┘  └──────────────────┘  └──────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘

Legend:
→  Data flow direction
▼  Process continuation  
┌─┐ Component boundaries
•  Key operations/features
```

## Key Flow Characteristics:

1. **Asynchronous**: Frontend uses async/await for non-blocking UI
2. **Tool-Driven**: Claude decides whether to search based on query type
3. **Session-Aware**: Maintains conversation context across queries
4. **Error-Resilient**: Each layer has error handling and fallbacks
5. **Semantic Search**: Uses embeddings for intelligent content matching
6. **Context-Rich**: Preserves course/lesson structure in responses