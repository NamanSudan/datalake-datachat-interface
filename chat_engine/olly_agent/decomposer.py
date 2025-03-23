import json
import re
import traceback
import boto3

class QueryDecomposer:
    def __init__(self, client, model):
        self.client = client
        self.model = model
        self.decomposition_prompt = """
        You are O11y's query decomposition component.
        
        Your task is to break down a user's query about observability data into components that will help generate accurate SQL.
        
        For the user's question, identify:
        1. INTENT: What is the primary goal? (finding errors, checking performance, etc.)
        2. TABLES: Which tables are likely needed? (Metrics, Logs, ServiceNow_Incidents_Local, AppdCis)
        3. FILTERS: What specific conditions or filters are required?
        4. TIME_RANGE: What time period is relevant?
        5. AGGREGATIONS: What calculations or groupings are needed?
        6. AMBIGUITIES: What parts of the question are unclear or need clarification?
        
        Format your response as a structured JSON with these fields.
        If clarification is needed from the user, include a "needs_followup" field set to true
        and a "followup_questions" array with specific questions.
        
        IMPORTANT: If the documentation already provides a clear example for this query, set "needs_followup" to false.
        """
    
    def decompose(self, user_query, user_responses=None, documentation_match=None):
        """Decompose a user query into structured components
        
        Args:
            user_query: The user's query
            user_responses: Any follow-up responses from the user
            documentation_match: Set to True if a documentation match was found
        """
        # If we already know this is a documented query, skip follow-up questions
        if documentation_match:
            print("Documentation match provided - skipping follow-up questions")
            return {
                "intent": "execute documented query",
                "tables": ["from_documentation"],
                "filters": ["from_documentation"],
                "time_range": "from_documentation",
                "aggregations": ["from_documentation"],
                "ambiguities": [],
                "needs_followup": False,
                "followup_questions": []
            }
            
        # If user already provided follow-up responses, don't ask for more
        if user_responses and len(user_responses) > 0:
            print(f"User has already provided {len(user_responses)} follow-up responses")
        
        # Combine user query with any follow-up responses
        context = f"User question: {user_query}\n\n"
        
        if user_responses and len(user_responses) > 0:
            context += "User has provided these additional details:\n"
            for i, response in enumerate(user_responses):
                context += f"{i+1}. {response}\n"
        
        # Check if client is properly initialized
        if not self.client:
            print("ERROR: LLM client is not initialized")
            return {
                "intent": "error",
                "tables": [],
                "error": "LLM client is not initialized",
                "needs_followup": True,
                "followup_questions": ["Internal error: LLM client not available. Please try again later."]
            }
        
        # Get decomposition from LLM
        try:
            print(f"Sending request to LLM with model: {self.model}")
            
            # Verify client type and print details
            client_type = type(self.client).__name__
            print(f"Client type: {client_type}")
            
            # Add special instruction to avoid unnecessary questions if user provided responses
            enhanced_prompt = self.decomposition_prompt
            if user_responses and len(user_responses) > 0:
                enhanced_prompt += "\n\nIMPORTANT: The user has already provided additional information, so set needs_followup to false even if some details remain unclear."
            
            # Prepare request payload
            system_message = [{"text": enhanced_prompt}]
            user_messages = [{"role": "user", "content": [{"text": context}]}]
            
            # Make the API call with detailed error capture
            try:
                print("Attempting API call...")
                response = self.client.converse(
                    modelId=self.model,
                    system=system_message,
                    messages=user_messages
                )
                print("API call successful!")
            except Exception as api_error:
                error_trace = traceback.format_exc()
                print(f"API call failed with error: {type(api_error).__name__}: {api_error}")
                print(f"Error trace: {error_trace}")
                
                # Check for specific error types
                if "AccessDeniedException" in str(api_error) or "UnauthorizedException" in str(api_error):
                    error_msg = "AWS Bedrock authentication failed - check credentials"
                elif "ResourceNotFoundException" in str(api_error):
                    error_msg = f"Model '{self.model}' not found - check model ID"
                elif "ValidationException" in str(api_error):
                    error_msg = "Invalid request format - check API parameters"
                elif "ServiceUnavailableException" in str(api_error) or "ThrottlingException" in str(api_error):
                    error_msg = "AWS Bedrock service temporarily unavailable"
                else:
                    error_msg = f"AWS Bedrock API call failed: {str(api_error)}"
                
                # Create a sensible decomposition with error info but don't necessarily ask for follow-up
                # unless this is the first attempt with no user responses
                return {
                    "intent": "error",
                    "tables": self.guess_tables_from_query(user_query),
                    "error": error_msg,
                    "api_error": str(api_error),
                    "needs_followup": not user_responses or len(user_responses) == 0,
                    "followup_questions": ["I encountered an error connecting to the language model. Please try again later."]
                }
            
            # Parse the LLM response and extract JSON
            decomposition = self.extract_json_from_response(response, user_query, user_responses)
            
            # If user provided follow-up responses, we should set needs_followup to false
            if user_responses and len(user_responses) > 0 and decomposition.get("needs_followup", False):
                print("User already provided responses - overriding needs_followup to false")
                decomposition["needs_followup"] = False
            
            return decomposition
            
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"ERROR in decompose method: {type(e).__name__}: {e}")
            print(f"Error trace: {error_trace}")
            
            # Try to extract some basic information from the query to avoid complete failure
            # Only ask for follow-up if this is the first attempt
            tables = self.guess_tables_from_query(user_query)
            
            return {
                "intent": "infer from query",
                "tables": tables,
                "error": f"Error in query decomposition: {str(e)}",
                "trace": error_trace,
                "needs_followup": not user_responses or len(user_responses) == 0,
                "followup_questions": [
                    "I encountered an error processing your question. Could you specify which database tables you want to query?",
                    "What specific information are you looking for?"
                ]
            }
            
    def guess_tables_from_query(self, query):
        """Make a basic guess at which tables might be relevant based on keywords"""
        query_lower = query.lower()
        tables = []
        
        # Look for key terms
        if any(term in query_lower for term in ["metric", "cpu", "memory", "performance", "database", "health"]):
            tables.append("Metrics")
            
        if any(term in query_lower for term in ["log", "error", "warning", "timeout", "message"]):
            tables.append("Logs")
            
        if any(term in query_lower for term in ["incident", "outage", "ticket", "service"]):
            tables.append("ServiceNow_Incidents_Local")
            
        if any(term in query_lower for term in ["controller", "agent", "ci", "appdynamics", "appd"]):
            tables.append("AppdCis")
            
        # Default to Metrics if nothing matched
        if not tables:
            tables.append("Metrics")
            
        return tables
            
    def extract_json_from_response(self, response, query, user_responses=None):
        """Extract and parse JSON from LLM response with robust error handling"""
        # Verify response structure
        if not response:
            print("ERROR: Empty response from API")
            return self.create_fallback_decomposition(query, user_responses)
        
        print(f"Response keys: {list(response.keys()) if response else 'None'}")
        
        if "output" not in response:
            print("ERROR: No 'output' key in response")
            return self.create_fallback_decomposition(query, user_responses)
        
        # Extract the text content
        content = None
        if "message" in response["output"]:
            content = response["output"]["message"].get("content", [])
        elif "content" in response["output"]:
            content = response["output"].get("content", [])
        else:
            print("ERROR: Could not find content in response")
            print(f"Output structure: {response['output']}")
            return self.create_fallback_decomposition(query, user_responses)
        
        if not content or len(content) == 0:
            print("ERROR: Empty content array")
            return self.create_fallback_decomposition(query, user_responses)
        
        # Get the text from the content
        decomposition_text = None
        if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
            decomposition_text = content[0]["text"]
        elif isinstance(content, str):
            decomposition_text = content
        else:
            print(f"Unexpected content structure: {content}")
            return self.create_fallback_decomposition(query, user_responses)
        
        print(f"Decomposition text preview: {decomposition_text[:100]}...")
        
        # Extract JSON from the response
        try:
            # Find JSON in the text (it might be wrapped in ```json blocks)
            try:
                json_match = re.search(r'```(?:json)?\n(.*?)```', decomposition_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    print("Found JSON in code block")
                else:
                    # Try alternative JSON pattern with different markers
                    json_match = re.search(r'```(?:json)?\s*(.*?)```', decomposition_text, re.DOTALL) 
                    if json_match:
                        json_str = json_match.group(1)
                        print("Found JSON in code block with alternative pattern")
                    else:
                        # Try to find JSON enclosed in triple backticks without json marker
                        json_match = re.search(r'```\s*(.*?)```', decomposition_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            print("Found possible JSON in generic code block")
                        else:
                            json_str = decomposition_text
                            print("Using entire response as JSON")
            except re.error as regex_error:
                print(f"ERROR: Regex error when searching for JSON block: {str(regex_error)}")
                json_str = decomposition_text
                print("Falling back to using entire response as JSON due to regex error")
                
            # Log the JSON string for debugging
            print(f"JSON string preview (first 200 chars): {json_str[:200]}...")
                
            # Parse the JSON
            try:
                decomposition = json.loads(json_str)
                print(f"Successfully parsed JSON with keys: {list(decomposition.keys())}")
                
                # If user provided follow-up responses, override needs_followup
                if user_responses and len(user_responses) > 0:
                    decomposition["needs_followup"] = False
                    print("User already provided responses, setting needs_followup=False")
                
                return decomposition
                
            except json.JSONDecodeError as json_error:
                print(f"JSON decode error: {json_error}")
                print(f"Failed to parse text: {json_str[:200]}...")
                
                # Try to clean the JSON string before giving up
                try:
                    # Remove any non-JSON content before first { or after last }
                    cleaned_str = re.search(r'(\{.*\})', json_str, re.DOTALL)
                    if cleaned_str:
                        json_str = cleaned_str.group(1)
                        print(f"Extracted JSON object: {json_str[:100]}...")
                        decomposition = json.loads(json_str)
                        print("Successfully parsed JSON after cleaning")
                        
                        # Set needs_followup based on user responses
                        if user_responses and len(user_responses) > 0:
                            decomposition["needs_followup"] = False
                            
                        return decomposition
                    else:
                        raise ValueError("No JSON object found in response")
                except Exception as e:
                    print(f"Failed to clean and parse JSON: {str(e)}")
                    return self.create_fallback_decomposition(query, user_responses)
            
        except Exception as e:
            print(f"Unexpected error parsing JSON response: {str(e)}")
            import traceback
            traceback_text = traceback.format_exc()
            print(f"Traceback: {traceback_text}")
            
            return self.create_fallback_decomposition(query, user_responses)
            
    def create_fallback_decomposition(self, query, user_responses=None):
        """Create a fallback decomposition when parsing fails"""
        tables = self.guess_tables_from_query(query)
        
        # Only ask for follow-up if this is the first attempt (no user responses)
        needs_followup = not user_responses or len(user_responses) == 0
        
        return {
            "intent": "parse_error_fallback",
            "tables": tables,
            "filters": [],
            "time_range": "recent",
            "aggregations": [],
            "ambiguities": ["Error occurred during decomposition"],
            "needs_followup": needs_followup,
            "followup_questions": [
                "Could you specify which tables you want to query?", 
                "What time period are you interested in?"
            ] if needs_followup else []
        }