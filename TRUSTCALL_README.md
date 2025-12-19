# TrustCall Integration for AI Tutoring Webhook

This implementation adds comprehensive monitoring and reliability tracking to the AI tutoring webhook system using TrustCall principles.

## Features Implemented

### 1. Webhook Monitoring
- **Request/Response Tracking**: Monitors all incoming webhook calls
- **Payload Validation**: Validates whiteboard state and required fields
- **Error Handling**: Comprehensive error catching and logging
- **Success Rate Tracking**: Monitors webhook success/failure rates

### 2. AI Performance Monitoring
- **API Call Tracking**: Monitors all OpenAI API calls (GPT-4.1, GPT-4o)
- **Response Time Measurement**: Tracks AI response times
- **Error Rate Monitoring**: Tracks AI API failures
- **Model Performance**: Tracks success rates per AI model

### 3. Whiteboard Generation Monitoring
- **Generation Attempts**: Tracks whiteboard generation attempts
- **Preview Generation**: Monitors whiteboard preview creation
- **Validation**: Validates whiteboard payload structure
- **Success Tracking**: Monitors whiteboard generation success rates

### 4. Metrics and Alerting
- **Real-time Metrics**: `/trustcall/metrics` endpoint for monitoring dashboard
- **Performance Metrics**: Response times, success rates, error counts
- **Alerting Thresholds**: Configurable thresholds for failure rates
- **Error Logging**: Detailed error logging with context

## API Endpoints

### Main Webhook
- `POST /receive` - Main webhook endpoint with TrustCall monitoring

### Monitoring Endpoints
- `GET /health_check` - Health check endpoint
- `GET /trustcall/metrics` - TrustCall metrics and monitoring data

## Metrics Provided

The `/trustcall/metrics` endpoint provides:

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "webhook_metrics": {
    "total_calls": 150,
    "successes": 145,
    "failures": 5,
    "success_rate": 96.67
  },
  "ai_api_metrics": {
    "total_calls": 300,
    "successes": 295,
    "failures": 5,
    "success_rate": 98.33
  },
  "whiteboard_metrics": {
    "total_generations": 75,
    "successes": 70,
    "failures": 5,
    "success_rate": 93.33
  },
  "performance_metrics": {
    "avg_response_time": 2.45,
    "payload_validation_errors": 2
  }
}
```

## TrustCall Event Logging

All events are logged with the following structure:

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "event_type": "webhook_call|ai_api_call|whiteboard_generation|payload_validation_error",
  "success": true|false,
  "details": {
    "endpoint": "/receive",
    "method": "POST",
    "response_time": 2.45,
    "error": "Error message if applicable"
  }
}
```

## Configuration

TrustCall settings can be configured in `trustcall_config.py`:

- **Webhook Monitoring**: Enable/disable webhook tracking
- **AI Monitoring**: Configure AI API monitoring settings
- **Whiteboard Monitoring**: Configure whiteboard generation tracking
- **Alerting Thresholds**: Set failure rate and performance thresholds
- **Metrics Collection**: Configure what metrics to collect

## Error Handling

The implementation includes comprehensive error handling:

1. **Payload Validation**: Validates incoming webhook payloads
2. **Whiteboard Validation**: Validates whiteboard state structure
3. **AI API Error Handling**: Catches and logs AI API errors
4. **Global Error Handler**: Catches all unhandled exceptions
5. **Response Time Tracking**: Tracks performance metrics

## Monitoring Dashboard Integration

To integrate with a TrustCall dashboard:

1. **Health Check**: Use `/health_check` for uptime monitoring
2. **Metrics**: Poll `/trustcall/metrics` for real-time metrics
3. **Logs**: Monitor application logs for TrustCall events
4. **Alerts**: Set up alerts based on configured thresholds

## Usage

The TrustCall integration is automatically enabled when the Flask app starts. All monitoring happens transparently without affecting the core functionality.

### Viewing Metrics
```bash
curl http://localhost:5000/trustcall/metrics
```

### Health Check
```bash
curl http://localhost:5000/health_check
```

## Benefits

1. **Reliability**: Track webhook success rates and identify issues
2. **Performance**: Monitor AI response times and optimize performance
3. **Debugging**: Detailed error logging for troubleshooting
4. **Alerting**: Proactive monitoring of failure rates
5. **Analytics**: Historical performance data for optimization

This TrustCall integration ensures your AI tutoring webhook system is reliable, performant, and easily monitorable.
