"""Custom log filters for reducing noise in logs."""
import logging

# Noisy endpoints that should not pollute logs at INFO level
EXCLUDED_PATHS = {
    '/api/scm/status',
    '/api/health',
    '/api/logs/frontend',
}


class ExcludeNoisyEndpointsFilter(logging.Filter):
    """Filter out log records for frequently polled endpoints to reduce log noise.
    
    These endpoints are typically polled every second and create excessive log entries.
    They can still be seen at DEBUG level if needed for troubleshooting.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to exclude the record from logging.
        
        Args:
            record: The log record to filter
            
        Returns:
            False if the record should be filtered out, True otherwise
        """
        message = record.getMessage()
        
        # Filter out access logs for excluded paths
        for path in EXCLUDED_PATHS:
            if path in message:
                return False
                
        return True
