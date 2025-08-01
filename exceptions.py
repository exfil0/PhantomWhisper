# phantom_whisper/exceptions.py

class PhantomWhisperError(Exception):
    """Base exception for all Phantom Whisper errors."""
    pass

class OrchestrationError(PhantomWhisperError):
    """Errors related to the overall orchestration flow."""
    pass

class LeakTimeoutError(OrchestrationError):
    """Specific error for when ASLR leak cannot be obtained within retries."""
    pass

class CommandDispatchError(OrchestrationError):
    """Specific error when a C2 command dispatch fails."""
    pass

class PayloadError(PhantomWhisperError):
    """Errors related to loading or handling exploit payloads."""
    pass

class WhatsAppTransportError(PhantomWhisperError):
    """Errors related to sending data via WhatsApp's protocol."""
    pass

class C2Error(PhantomWhisperError):
    """Base for C2 comms errors."""
    pass

class C2RequestFailed(C2Error):
    """Indicates C2 HTTP request failed (network, 4xx, 5xx)"""
    pass

class C2ResponseSchemaError(C2Error):
    """Indicates C2 response did not meet expected JSON schema/status."""
    pass
