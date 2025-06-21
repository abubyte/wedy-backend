# Payme Integration Guide

This guide provides detailed information about the Payme payment integration in the Wedy backend API.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [API Reference](#api-reference)
5. [Database Schema](#database-schema)
6. [Error Handling](#error-handling)
7. [Testing](#testing)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)

## Overview

The Payme integration allows users to purchase tariffs using Uzcard and HUMO cards through the Payme payment gateway. The integration includes:

- Payment creation and management
- Webhook handling for payment notifications
- Automatic tariff activation
- Comprehensive error handling
- Security measures

## Architecture

### Components

1. **PaymeService** (`app/external_services/payme_service.py`)
   - Handles all Payme API interactions
   - Manages signature generation and verification
   - Provides payment creation, status checking, and cancellation

2. **PaymeRouter** (`app/routers/payme_router.py`)
   - Exposes payment endpoints
   - Handles webhook processing
   - Manages payment status checking

3. **Payment CRUD** (`app/crud/payment_crud.py`)
   - Database operations for payments
   - Payment status management
   - Tariff activation logic

4. **Payment Models** (`app/models/payment_model.py`)
   - Database schema for payments
   - Payme-specific fields

### Flow Diagram

```
User → Tariff Purchase → Create Payment → Payme API → Payment URL
                                                      ↓
Webhook ← Payme ← Payment Completion ← User Payment ← Payment Page
   ↓
Update Status → Activate Tariff → User Access
```

## Configuration

### Environment Variables

```env
# Required
PAYME_MERCHANT_ID=your_merchant_id
PAYME_SECRET_KEY=your_secret_key

# Optional (with defaults)
PAYME_TEST_MODE=true
PAYME_CALLBACK_URL=https://api.wedy.uz/payme/webhook
PAYME_API_URL=https://checkout.paycom.uz
PAYME_TEST_API_URL=https://test.paycom.uz
```

### Payme Dashboard Configuration

1. **Webhook URL**: Set to `https://api.wedy.uz/payme/webhook`
2. **Signature Verification**: Enabled (HMAC-SHA256)
3. **Supported Events**: `receipts.pay`, `receipts.cancel`

## API Reference

### Payment Endpoints

#### Create Payment

```http
POST /payme/create-payment
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": "user123",
  "tariff_id": 1,
  "amount": 50000,
  "description": "Premium Tariff"
}
```

**Response:**
```json
{
  "success": true,
  "transaction_id": "64f8a1b2c3d4e5f6a7b8c9d0",
  "cheque_id": "cheque123",
  "pay_url": "https://checkout.paycom.uz/payment/...",
  "data": {...}
}
```

#### Webhook Endpoint

```http
POST /payme/webhook
X-Auth-Signature: <hmac_signature>
Content-Type: application/json

{
  "method": "receipts.pay",
  "params": {
    "id": "64f8a1b2c3d4e5f6a7b8c9d0",
    "cheque_id": "cheque123",
    "amount": 5000000,
    "paid_at": 1642234567
  }
}
```

**Response:**
```json
{
  "result": "ok"
}
```

#### Check Transaction Status

```http
GET /payme/check-status/{transaction_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "status": "PAID",
  "amount": 5000000,
  "paid_at": "2024-01-15T10:30:00Z",
  "data": {...}
}
```

### Tariff Endpoints

#### Purchase Tariff

```http
POST /tariffs/{tariff_id}/purchase
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Payment created successfully. Please complete the payment using the provided URL.",
  "tariff": {
    "id": 1,
    "name": "Premium Plan",
    "price": 50000,
    "duration_days": 30,
    "is_active": true
  },
  "payment_url": "https://checkout.paycom.uz/payment/...",
  "transaction_id": "64f8a1b2c3d4e5f6a7b8c9d0"
}
```

## Database Schema

### Payment Table

```sql
CREATE TABLE payment (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    amount INTEGER NOT NULL,
    status VARCHAR DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP NULL,
    
    -- Payme-specific fields
    payme_transaction_id VARCHAR NULL,
    payme_cheque_id VARCHAR NULL,
    tariff_id INTEGER NULL,
    payment_method VARCHAR DEFAULT 'PAYME',
    payme_error_code VARCHAR NULL,
    payme_error_message VARCHAR NULL,
    
    -- Tracking fields
    updated_at TIMESTAMP NULL,
    webhook_received_at TIMESTAMP NULL
);

-- Indexes
CREATE INDEX idx_payment_user_id ON payment(user_id);
CREATE INDEX idx_payment_payme_transaction_id ON payment(payme_transaction_id);
CREATE INDEX idx_payment_status ON payment(status);
CREATE INDEX idx_payment_created_at ON payment(created_at);
```

### User Table Updates

```sql
ALTER TABLE user ADD COLUMN tariff_id INTEGER NULL;
ALTER TABLE user ADD COLUMN tariff_expires_at TIMESTAMP NULL;

-- Foreign key constraint
ALTER TABLE user ADD CONSTRAINT fk_user_tariff 
    FOREIGN KEY (tariff_id) REFERENCES tariff(id);
```

## Error Handling

### Exception Classes

```python
class PaymeError(Exception):
    """Base exception for Payme-related errors"""
    pass

class PaymeAPIError(PaymeError):
    """Exception for Payme API errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data
        super().__init__(self.message)

class PaymeValidationError(PaymeError):
    """Exception for Payme validation errors"""
    pass
```

### Error Response Format

```json
{
  "success": false,
  "error": "Error message",
  "data": {
    "error_code": "PAYME_API_ERROR",
    "response_data": {...}
  }
}
```

### Common Error Codes

- `PAYME_CREATE_FAILED` - Payment creation failed
- `PAYME_API_ERROR` - Payme API error
- `VALIDATION_ERROR` - Input validation error
- `WEBHOOK_FAILED` - Webhook processing error

## Testing

### Test Environment Setup

1. **Enable Test Mode**
   ```env
   PAYME_TEST_MODE=true
   ```

2. **Use Test Credentials**
   - Get test credentials from Payme dashboard
   - Use sandbox environment

3. **Test Webhook URL**
   - Use ngrok for local testing: `ngrok http 8000`
   - Update webhook URL in Payme dashboard

### Test Payment Flow

1. **Create Test Tariff**
   ```bash
   curl -X POST "http://localhost:8000/tariffs" \
     -H "Authorization: Bearer <admin_token>" \
     -F "name=Test Tariff" \
     -F "price=1000" \
     -F "duration_days=7"
   ```

2. **Purchase Tariff**
   ```bash
   curl -X POST "http://localhost:8000/tariffs/1/purchase" \
     -H "Authorization: Bearer <user_token>"
   ```

3. **Complete Payment**
   - Open payment URL in browser
   - Use test card: `8600 1234 5678 9012`
   - Complete payment

4. **Verify Webhook**
   - Check logs for webhook processing
   - Verify payment status update
   - Confirm tariff activation

### Test Cards

| Card Type | Number | Expiry | CVV |
|-----------|--------|--------|-----|
| Uzcard | 8600 1234 5678 9012 | Any future date | Any 3 digits |
| HUMO | 9860 1234 5678 9012 | Any future date | Any 3 digits |

## Security

### Webhook Security

1. **Signature Verification**
   ```python
   def verify_webhook_signature(self, data: Dict[str, Any], signature: str) -> bool:
       # Generate expected signature
       expected_signature = self._generate_signature(data)
       
       # Compare signatures
       return hmac.compare_digest(signature, expected_signature)
   ```

2. **Input Validation**
   - Validate webhook payload structure
   - Check required fields
   - Verify data types

### API Security

1. **Authentication**
   - JWT token required for payment endpoints
   - Admin authentication for sensitive operations

2. **Input Sanitization**
   - Validate all input parameters
   - Sanitize user-provided data
   - Prevent SQL injection

3. **Error Handling**
   - No sensitive data in error messages
   - Proper HTTP status codes
   - Comprehensive logging

## Troubleshooting

### Common Issues

#### 1. Webhook Not Received

**Symptoms:**
- Payment completed but tariff not activated
- No webhook logs in application

**Solutions:**
- Verify webhook URL in Payme dashboard
- Check server accessibility
- Ensure HTTPS for production
- Verify signature validation

#### 2. Payment Creation Failed

**Symptoms:**
- API returns error on payment creation
- No transaction ID received

**Solutions:**
- Check Payme credentials
- Verify tariff exists and is active
- Check amount validation
- Review Payme API response

#### 3. Tariff Not Activated

**Symptoms:**
- Payment successful but tariff not active
- User still has old tariff

**Solutions:**
- Check webhook processing logs
- Verify payment status in Payme
- Check tariff activation logic
- Review database transactions

### Debug Steps

1. **Check Logs**
   ```bash
   tail -f app.log | grep -i payme
   ```

2. **Verify Database**
   ```sql
   SELECT * FROM payment WHERE payme_transaction_id = 'transaction_id';
   SELECT * FROM user WHERE id = 'user_id';
   ```

3. **Test Payme API**
   ```bash
   curl -X POST "https://test.paycom.uz/api" \
     -H "Content-Type: application/json" \
     -H "X-Auth: merchant_id:signature" \
     -d '{"method":"receipts.get","params":{"id":"transaction_id"}}'
   ```

### Monitoring

#### Key Metrics

1. **Payment Success Rate**
   ```sql
   SELECT 
     COUNT(*) as total_payments,
     COUNT(CASE WHEN status = 'PAID' THEN 1 END) as successful_payments,
     (COUNT(CASE WHEN status = 'PAID' THEN 1 END) * 100.0 / COUNT(*)) as success_rate
   FROM payment;
   ```

2. **Webhook Processing**
   ```sql
   SELECT 
     COUNT(*) as total_webhooks,
     COUNT(CASE WHEN webhook_received_at IS NOT NULL THEN 1 END) as processed_webhooks
   FROM payment;
   ```

3. **Error Rates**
   ```sql
   SELECT 
     payme_error_code,
     COUNT(*) as error_count
   FROM payment 
   WHERE payme_error_code IS NOT NULL
   GROUP BY payme_error_code;
   ```

#### Alerts

Set up alerts for:
- Payment failure rate > 5%
- Webhook processing delays
- API error rates
- Database connection issues

## Production Checklist

- [ ] Set `PAYME_TEST_MODE=false`
- [ ] Use production Payme credentials
- [ ] Configure production webhook URL
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Set up monitoring and alerts
- [ ] Configure backup and recovery
- [ ] Test payment flow in production
- [ ] Monitor logs and metrics
- [ ] Set up error reporting
- [ ] Document incident response procedures

## Support

For Payme-specific issues:
- Payme Business Support: https://business.paycom.uz/support
- Payme API Documentation: https://developer.help.paycom.uz/

For application issues:
- Check application logs
- Review error messages
- Contact development team 