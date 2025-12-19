"""
TrustCall Configuration for AI Tutoring Webhook Monitoring

This configuration file contains settings for TrustCall monitoring integration
to track webhook reliability, AI performance, and whiteboard generation success.
"""

# TrustCall Monitoring Configuration
TRUSTCALL_CONFIG = {
    # Webhook monitoring settings
    'webhook_monitoring': {
        'enabled': True,
        'log_level': 'INFO',
        'max_retries': 3,
        'timeout_seconds': 30
    },
    
    # AI API monitoring settings
    'ai_monitoring': {
        'enabled': True,
        'track_response_times': True,
        'track_token_usage': False,  # Set to True if you want to track OpenAI token usage
        'models_to_monitor': ['gpt-4.1', 'gpt-4o']
    },
    
    # Whiteboard monitoring settings
    'whiteboard_monitoring': {
        'enabled': True,
        'validate_payloads': True,
        'track_generation_attempts': True,
        'max_attempts': 3
    },
    
    # Alerting thresholds
    'alerting': {
        'webhook_failure_rate_threshold': 10.0,  # Alert if failure rate > 10%
        'ai_api_failure_rate_threshold': 5.0,    # Alert if AI API failure rate > 5%
        'whiteboard_failure_rate_threshold': 15.0, # Alert if whiteboard failure rate > 15%
        'response_time_threshold': 30.0,          # Alert if avg response time > 30 seconds
        'payload_validation_error_threshold': 5   # Alert if validation errors > 5
    },
    
    # Metrics collection
    'metrics': {
        'collect_response_times': True,
        'collect_success_rates': True,
        'collect_error_details': True,
        'metrics_endpoint': '/trustcall/metrics'
    }
}

# TrustCall Dashboard Integration
DASHBOARD_CONFIG = {
    'base_url': 'http://localhost:5000',
    'endpoints': {
        'health_check': '/health_check',
        'metrics': '/trustcall/metrics',
        'webhook': '/receive'
    },
    'refresh_interval': 30  # seconds
}

# Logging configuration for TrustCall
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'trustcall': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - TrustCall: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'trustcall',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'trustcall.log',
            'formatter': 'trustcall',
            'level': 'INFO'
        }
    },
    'loggers': {
        'trustcall': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
