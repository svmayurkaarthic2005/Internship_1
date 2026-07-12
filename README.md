# Sub Inspector Surveyor AI Assistant

## Overview

A bilingual (Tamil/English) AI-powered chatbot system designed to assist Sub Inspectors in managing survey applications. The system provides intelligent query handling, application tracking, document verification, and workflow management through natural language conversations.

## Features

### Core Functionality
- **Bilingual Support**: Fully supports Tamil, English, and Tanglish (Tamil written in English)
- **Intelligent Intent Detection**: Automatically identifies user intent from natural language queries
- **RAG-based Architecture**: Uses Retrieval-Augmented Generation with ChromaDB for accurate responses
- **Real-time Streaming**: SSE-based streaming responses for better user experience
- **Context Awareness**: Maintains conversation continuity and implicit application references
- **Voice Support**: Text-to-speech and speech-to-text capabilities

### Application Management
- **Application Status Tracking**: Query status, stage, and workflow history
- **Document Verification**: Check uploaded documents and identify missing ones
- **Joint Owner Queries**: Identify joint owners for applications or survey numbers
- **Sale Deed Verification**: Validate sale deed registration status
- **Type Classification**: Identify ISD/NISD/MERGE application types
- **Field-specific Queries**: Get specific application fields (name, mobile, email, address, etc.)

### Advanced Features
- **Spelling Error Handling**: Tolerates common spelling mistakes in Tamil and English
- **Implicit Continuation**: Maintains context from previous messages for follow-up queries
- **Smart Application Number Extraction**: Identifies application numbers from various formats
- **Table Rendering**: Presents structured data in clean, formatted tables
- **Fallback Mechanisms**: Graceful handling of ambiguous or unclear queries

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with asyncpg
- **Vector Store**: ChromaDB for semantic search
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **LLM Integration**: OpenAI-compatible API (Groq)
- **Authentication**: JWT-based auth system

### Frontend
- **HTML/CSS/JavaScript**: Vanilla JS with modern CSS
- **Speech API**: Web Speech API for voice features
- **Storage**: LocalStorage for chat history persistence
- **Streaming**: EventSource API for SSE

### Infrastructure
- **Environment**: Python 3.8+
- **Package Management**: pip, requirements.txt
- **Process Management**: Batch scripts for Windows

## Project Structure

```
nic_internship/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connection pooling
│   ├── dependencies.py         # Dependency injection
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── routers/
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── chat.py            # Chat endpoints
│   │   ├── applications.py   # Application management
│   │   ├── survey.py          # Survey endpoints
│   │   └── speech.py          # Speech-to-text/text-to-speech
│   ├── services/
│   │   ├── chatbot.py         # Main chatbot logic
│   │   ├── rag.py             # RAG intent detection & query routing
│   │   ├── postgres.py        # PostgreSQL query handlers
│   │   ├── chroma.py          # ChromaDB vector store
│   │   ├── embeddings.py      # Embedding generation
│   │   ├── auth_service.py    # Authentication logic
│   │   └── speech_service.py  # Speech processing
│   ├── utils/
│   │   ├── logger.py          # Logging configuration
│   │   └── helpers.py         # Utility functions
│   └── documents/
│       ├── faq_english.txt    # English FAQ
│       ├── faq_tamil.txt      # Tamil FAQ
│       ├── survey_manual.txt  # Survey manual
│       └── workflow_guide.txt # Workflow documentation
├── frontend/
│   ├── login.html             # Login page
│   ├── chatbot.html           # Main chat interface
│   ├── css/                   # Stylesheets
│   │   ├── global.css         # Global styles
│   │   ├── variables.css      # CSS variables
│   │   ├── components.css     # Component styles
│   │   ├── chatbot.css        # Chat-specific styles
│   │   ├── animations.css     # Animations
│   │   └── responsive.css     # Responsive design
│   └── js/                    # JavaScript modules
│       ├── auth.js            # Authentication handling
│       ├── chat.js            # Chat logic
│       ├── chatStorage.js     # Chat history storage
│       ├── dataTable.js       # Table rendering
│       ├── speechAPI.js       # Speech API integration
│       └── voiceRecorder.js   # Voice recording
├── vectorstore/
│   └── chroma.sqlite3         # ChromaDB database
├── .env                       # Environment variables (not in repo)
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
└── start_backend.bat          # Backend startup script
```

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Git

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nic_internship
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   copy .env.example .env
   # Edit .env with your configuration
   ```

5. **Setup database**
   ```bash
   python create_database.py
   python backend/seed.py
   ```

6. **Ingest documents into vector store**
   ```bash
   python backend/ingest.py
   ```

7. **Start the backend**
   ```bash
   start_backend.bat
   # Or manually:
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **Open frontend**
   - Navigate to `http://localhost:8000/frontend/login.html`
   - Default credentials: admin / admin123

## Configuration

### Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# API Keys
GROQ_API_KEY=your_groq_api_key_here

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Vector Store
CHROMA_PERSIST_DIR=./vectorstore
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Application
API_URL=http://localhost:8000
```

## Key Features & Implementation

### 1. Intent Detection & Routing

**File**: `backend/services/rag.py`

The system uses a multi-stage intent detection pipeline:

```python
# Intent priority order:
1. greeting                    # Welcome messages
2. farewell                    # Goodbye messages  
3. joint_owner_check          # Joint owner queries (MOVED BEFORE app_status)
4. application_status         # Application tracking
5. check_documents            # Document verification
6. check_sale_deed           # Sale deed validation
7. is_nisd_or_isd            # Application type
8. field_specific_query      # Specific field queries
9. ask_application_survey_no # Ask for app number
10. general_query            # Fallback to RAG
```

**Key Enhancements**:
- Tamil keyword support for all intents
- Tanglish pattern matching
- Spelling error tolerance
- Context-aware detection

### 2. Hallucination Prevention

**Problem**: Chatbot was inventing application numbers when users used generic references like "the name"

**Solution** (Lines ~51-95 in chatbot.py):
```python
def _extract_app_number_from_context(
    self, 
    message: str, 
    history: list, 
    allow_implicit_continuation: bool = False
) -> Optional[str]:
    """
    Extract application number from current message or chat history.
    
    Rules:
    1. Explicit mention: "APP-2024-000001" → returns it
    2. Reference patterns: "this/that application" → checks last 2 messages
    3. Implicit continuation: field queries → checks last 2 messages
    4. No reference found → returns None (prevents hallucination)
    """
    # Strict patterns to avoid false positives
    reference_patterns = [
        r'\b(?:this|that|the)\s+application\b',
        r'\b(?:above|previous|same)\s+(?:application|one)\b',
    ]
```

**Before Fix**: "what is the name" → Hallucinated APP-2024-000001
**After Fix**: "what is the name" → "Please provide an application number"

### 3. Implicit Continuation

**Feature**: Maintains context from previous messages for follow-up queries

**Implementation** (Lines ~1099-1130 in chatbot.py):
```python
# User: "tell me about APP-2024-000001"
# Bot: Shows application details
# User: "what is the applicant name?"  ← Implicit reference
# Bot: Uses APP-2024-000001 from context
```

**Activation**: Only for field-specific queries (name, mobile, email, address, etc.)

### 4. Joint Owner Queries

**Feature**: Check joint owners for applications or survey numbers

**Tamil Support** (Lines ~1997-2023, ~3465-3495 in chatbot.py):
```python
# Tamil keywords:
- கூட்டுரிமையாளர் (kootturrimaiyalar)
- உரிமையாளர்கள் (urimaiyalargal)
- ஒரே உரிமையாளர் (ore urimaiyalar)
- joint owner, co-owner (Tanglish)

# Responses:
- English: "For application APP-2024-000001 (Survey 145): There are 2 joint owner(s) listed: Owner A, Owner B."
- Tamil: "விண்ணப்பம் APP-2024-000001 (கணக்கெண் 145): 2 கூட்டு உரிமையாளர்கள் உள்ளனர்: Owner A, Owner B."
```

**Database Query** (postgres.py):
```python
async def get_joint_owners(app_number: str, survey_no: str):
    # Returns all owners except the applicant
    # Supports both application number and survey number queries
```

### 5. Bilingual Response System

**Language Detection** (rag.py):
```python
def detect_language(text: str) -> str:
    tamil_chars = re.findall(r'[\u0B80-\u0BFF]', text)
    if len(tamil_chars) > 3:
        return "ta"  # Tamil script
    
    # Check Tanglish patterns
    tanglish_patterns = ['endha', 'epdi', 'enna', 'enga', ...]
    if any(pattern in text.lower() for pattern in tanglish_patterns):
        return "tanglish"
    
    return "en"  # English
```

**Response Builder Pattern**:
```python
# Every response builder checks language
is_tamil = language in ("ta", "tanglish")

if is_tamil:
    chunk = "தமிழ் பதில்"
else:
    chunk = "English response"
```

### 6. Spelling Error Handling

**Implementation**: Uses fuzzy matching and phonetic similarity

**Examples**:
- "aplication" → "application" ✓
- "servey" → "survey" ✓
- "விண்ணப்பம்" variations ✓
- "உரிமையாலர்" → "உரிமையாளர்" ✓

### 7. Table Rendering

**Feature**: Presents structured data in clean tables

**Configuration** (Lines ~3645, ~3978 in chatbot.py):
```python
# Intents that show tables:
table_intents = [
    "application_status",  # When multiple apps found
    "check_documents",     # Document list
    # joint_owner_check excluded - uses prose response
]
```

**Rendering** (frontend/js/dataTable.js):
```javascript
// Automatically detects table data from structured_data
// Renders sortable, filterable tables
// Supports Tamil and English column headers
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/me` - Get current user

### Chat
- `POST /chat` - Send message (JSON response)
- `POST /chat/stream` - Send message (SSE streaming)
- `GET /chat/history` - Get chat history
- `DELETE /chat/history` - Clear chat history

### Applications
- `GET /applications` - List all applications
- `GET /applications/{id}` - Get application details
- `PUT /applications/{id}` - Update application
- `POST /applications` - Create application

### Survey
- `GET /survey/numbers` - List survey numbers
- `GET /survey/{survey_no}` - Get survey details

### Speech
- `POST /speech/synthesize` - Text-to-speech
- `POST /speech/transcribe` - Speech-to-text

## Database Schema

### Key Tables

**applications**
- id, application_number, applicant_name, mobile, email
- type (ISD/NISD/MERGE), status, stage, survey_no
- submission_date, created_at, updated_at

**ownership**
- id, survey_no, owner_name, owner_type
- share_percentage, joint_owner_flag

**documents**
- id, application_id, document_type
- is_uploaded, upload_date, file_path

**workflow_history**
- id, application_id, stage, action
- officer_name, timestamp, remarks

**users**
- id, username, email, hashed_password
- role, created_at, is_active

## Testing

### Test Files
- `test_auth.py` - Authentication tests
- `test_db_connection.py` - Database connectivity
- `test_integration.py` - End-to-end tests
- `test_streaming.py` - SSE streaming tests
- `test_tamil_query.py` - Tamil language tests
- `test_speech_direct.py` - Speech API tests

### Run Tests
```bash
# Run all tests
python -m pytest

# Run specific test
python test_tamil_query.py
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check PostgreSQL is running
   # Verify .env DATABASE_URL
   python test_db_connection.py
   ```

2. **ChromaDB Not Loading**
   ```bash
   # Re-ingest documents
   python backend/ingest.py
   ```

3. **Backend Not Starting**
   ```bash
   # Check port availability
   netstat -ano | findstr :8000
   # Kill process if needed
   taskkill /PID <pid> /F
   ```

4. **Tamil Not Displaying**
   - Ensure UTF-8 encoding in all files
   - Check browser supports Tamil fonts
   - Verify `Content-Type: text/html; charset=utf-8`

5. **Hallucination Issues**
   - Check `_extract_app_number_from_context()` logic
   - Verify intent detection priority in rag.py
   - Review chat history structure

## Performance Optimization

### Database Indexes
```sql
-- Applied via apply_indexes.sql
CREATE INDEX idx_applications_number ON applications(application_number);
CREATE INDEX idx_applications_survey ON applications(survey_no);
CREATE INDEX idx_ownership_survey ON ownership(survey_no);
CREATE INDEX idx_workflow_app ON workflow_history(application_id);
```

### Caching Strategy
- ChromaDB embeddings cached in vectorstore/
- Chat history stored in localStorage
- Token-based auth reduces DB queries

### Streaming Benefits
- SSE streaming reduces perceived latency
- Chunks sent as generated (not waiting for full response)
- Better UX for long responses

## Security Considerations

- JWT tokens with expiration
- Password hashing with bcrypt
- SQL injection prevention via parameterized queries
- CORS configuration for API endpoints
- Input validation on all endpoints
- Rate limiting on chat endpoints

## Future Enhancements

- [ ] Multi-file upload support
- [ ] Advanced search with filters
- [ ] Analytics dashboard
- [ ] Email notifications
- [ ] Mobile app version
- [ ] More language support (Hindi, Telugu, etc.)
- [ ] Voice-only mode
- [ ] Offline mode support
- [ ] Integration with GIS systems
- [ ] Automated report generation

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

This project is developed for National Informatics Centre (NIC) internship.

## Contact

For support or queries, contact the development team.

## Changelog

### Version 1.2 (Current)
- ✅ Fixed hallucination issues with application number extraction
- ✅ Added implicit continuation for field-specific queries
- ✅ Implemented joint owner queries with Tamil support
- ✅ Enhanced intent detection priority (joint_owner before app_status)
- ✅ Added Tamil response support for all intents
- ✅ Improved spelling error tolerance
- ✅ Removed empty table rendering for joint_owner_check
- ✅ Enhanced conversation context maintenance

### Version 1.1
- Added streaming response support
- Implemented bilingual (Tamil/English) support
- Added voice recording capabilities
- Enhanced RAG system with ChromaDB

### Version 1.0
- Initial release
- Basic chatbot functionality
- Application management system
- User authentication

## Acknowledgments

- National Informatics Centre (NIC)
- Tamil Nadu State Government
- All contributors and testers
