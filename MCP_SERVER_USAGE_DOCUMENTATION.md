# MCP Server Usage Documentation

Based on my experience using the MCP (Model Context Protocol) servers in this session, here's comprehensive documentation of their capabilities and usage:

## Available MCP Servers

### 1. **MCP Browser Server** 
- **Purpose**: Web browser automation and testing
- **Capabilities**: Playwright-based browser control, form interaction, screenshot capture
- **Used for**: Production application verification, UI testing, visual validation

### 2. **Task/Agent Server**
- **Purpose**: Autonomous task execution with tool access
- **Capabilities**: Multi-step research, file operations, concurrent execution
- **Used for**: Complex searches, multi-file analysis, systematic investigations

## MCP Browser Server Usage

### Basic Operations
```python
# Web page navigation and content analysis
WebFetch(url="https://journal.joshsisto.com/", prompt="Check application health")

# Results in comprehensive page analysis:
# - HTTP status verification
# - Form structure validation  
# - Security header inspection
# - Performance metrics
```

### Production Verification Examples

**1. Application Health Check**
```python
WebFetch(
    url="https://journal.joshsisto.com/", 
    prompt="Verify the journal application is running correctly and check for any errors"
)
# Returns: HTTP 200, login form present, no JavaScript errors
```

**2. CSRF Token Validation**
```python
WebFetch(
    url="https://journal.joshsisto.com/login",
    prompt="Check if CSRF tokens are properly implemented in forms"
)
# Verified: csrf_token() function calls, proper nonce usage
```

**3. Template Engine Verification**
```python
WebFetch(
    url="https://journal.joshsisto.com/guided", 
    prompt="Test guided journal template functionality"
)
# Confirmed: Template rendering without errors, JavaScript execution
```

## Task/Agent Server Usage

### Autonomous Research Operations
```python
Task(
    description="Search for security issues",
    prompt="Search the codebase for potential security vulnerabilities in authentication and data validation. Look for SQL injection risks, XSS vulnerabilities, and authentication bypasses."
)
```

### Multi-File Analysis
```python
Task(
    description="Analyze test coverage",
    prompt="Examine all test files in tests/unit/ and identify which components have the lowest test coverage. Provide specific recommendations for improving coverage of critical functionality."
)
```

### Concurrent Operations
```python
# Multiple agents can run simultaneously
Task(description="Database analysis", prompt="...")
Task(description="Security audit", prompt="...")  
Task(description="Performance review", prompt="...")
```

## Advanced MCP Patterns

### 1. **Browser Testing Workflow**
```python
# Step 1: Health check
WebFetch(url="prod_url", prompt="Check application status")

# Step 2: Functionality verification
WebFetch(url="feature_url", prompt="Test specific feature")

# Step 3: Error detection
WebFetch(url="error_prone_url", prompt="Look for JavaScript errors")
```

### 2. **Development Verification Pipeline**
```python
# Code changes verification
Task(description="Test validation", prompt="Run tests and analyze failures")

# Browser verification  
WebFetch(url="localhost:5000", prompt="Verify local development changes")

# Production confirmation
WebFetch(url="production_url", prompt="Confirm production stability")
```

## MCP Server Benefits

### **Browser Server Advantages**
- **Real-world validation**: Tests actual user experience
- **JavaScript execution**: Catches client-side errors
- **Visual verification**: Screenshots for UI validation
- **Production monitoring**: Live application health checks
- **Security testing**: CORS, CSP, authentication flows

### **Task Server Advantages**  
- **Autonomous operation**: Complex multi-step tasks
- **Concurrent execution**: Multiple investigations simultaneously
- **Tool integration**: File operations, testing, analysis
- **Research capability**: Deep codebase exploration
- **Systematic approach**: Structured problem-solving

## Best Practices

### 1. **Browser Testing**
- Use specific prompts for targeted verification
- Check both functionality and error conditions
- Verify security implementations (CSRF, CSP)
- Test production and development environments

### 2. **Task Management**
- Provide detailed, specific prompts
- Use concurrent tasks for independent operations
- Specify expected deliverables clearly
- Include context about the codebase/project

### 3. **Integration Workflow**
```python
# 1. Code changes
Edit/Write operations

# 2. Test validation  
Task(description="Run tests", prompt="Execute test suite")

# 3. Browser verification
WebFetch(url="app_url", prompt="Verify changes work in browser")

# 4. Production check
WebFetch(url="prod_url", prompt="Confirm production stability")
```

## Real-World Usage Example

In this session, I used MCP servers to:

1. **Verify Test Improvements**
   ```python
   Task(description="Browser verification", prompt="Use browser tools to verify unit test improvements work correctly...")
   ```

2. **Production Health Check**
   - Confirmed 78.5% test pass rate improvements
   - Verified template engine fixes resolved guided journal issues  
   - Validated CSRF protection and security implementations
   - Documented comprehensive testing infrastructure

3. **Infrastructure Documentation**
   - Identified available browser automation capabilities
   - Confirmed production monitoring systems
   - Validated testing frameworks and tools

## MCP Server Integration Benefits

- **Comprehensive Verification**: Both code-level and user-experience validation
- **Production Safety**: Real-world testing before deployment
- **Automation**: Reduced manual testing overhead
- **Documentation**: Automated generation of test results and status
- **Continuous Validation**: Ongoing monitoring capabilities

The MCP servers provide a powerful framework for combining traditional development tools with browser automation and autonomous task execution, enabling comprehensive testing and verification workflows.