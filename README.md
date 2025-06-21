# Wedy Backend API

A FastAPI-based backend service for the Wedy platform with integrated Payme payment processing.

## Features

- **User Authentication & Authorization**: JWT-based authentication with role-based access control
- **Tariff Management**: Subscription-based tariff system with Payme payment integration
- **Card Management**: Business card creation and management
- **Category Management**: Business categories and classification
- **Payment Processing**: Secure payment processing via Payme payment gateway
- **File Storage**: AWS S3 integration for file uploads
- **SMS & Email Services**: Communication services via Eskiz SMS and SMTP email

## Payme Payment Integration

### Overview

The application integrates with Payme payment gateway to process tariff subscriptions. Users can purchase tariffs using Uzcard and HUMO cards through the Payme platform.

### Configuration

Add the following environment variables to your `.env` file:

```env
# Payme Payment Gateway Configuration
PAYME_MERCHANT_ID=your_payme_merchant_id
PAYME_SECRET_KEY=your_payme_secret_key
PAYME_TEST_MODE=true  # Set to false for production
PAYME_CALLBACK_URL=https://api.wedy.uz/payme/webhook
PAYME_API_URL=https://checkout.paycom.uz
PAYME_TEST_API_URL=https://test.paycom.uz
```

### Getting Payme Credentials

1. Register at [Payme Business](https://business.paycom.uz)
2. Complete business verification process
3. Get your Merchant ID and Secret Key from the dashboard
4. Configure webhook URL in Payme dashboard

### Payment Flow

1. **User selects a tariff** → `POST /tariffs/{tariff_id}/purchase`
2. **System creates payment** → Creates local payment record and Payme transaction
3. **User completes payment** → Redirected to Payme payment page
4. **Payme sends webhook** → `POST /payme/webhook` (payment confirmation)
5. **System activates tariff** → Automatically activates user's tariff subscription

### API Endpoints

#### Payment Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/payme/create-payment` | Create a new Payme payment | User |
| POST | `/payme/webhook` | Handle Payme webhook notifications | None |
| GET | `/payme/check-status/{transaction_id}` | Check transaction status | User |
| POST | `/payme/purchase-tariff` | Purchase tariff via Payme | User |
| GET | `/payme/statistics` | Get payment statistics | Admin |
| POST | `/payme/cancel-payment/{transaction_id}` | Cancel payment | Admin |

#### Tariff Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/tariffs` | List all tariffs | User |
| GET | `/tariffs/{tariff_id}` | Get specific tariff | User |
| POST | `/tariffs/{tariff_id}/purchase` | Purchase tariff with Payme | User |
| POST | `/tariffs` | Create tariff | Admin |
| PUT | `/tariffs/{tariff_id}` | Update tariff | Admin |
| DELETE | `/tariffs/{tariff_id}` | Delete tariff | Admin |

### Request Examples

#### Purchase a Tariff

```bash
curl -X POST "https://api.wedy.uz/tariffs/1/purchase" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
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

#### Check Payment Status

```bash
curl -X GET "https://api.wedy.uz/payme/check-status/64f8a1b2c3d4e5f6a7b8c9d0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "status": "PAID",
  "amount": 5000000,
  "paid_at": "2024-01-15T10:30:00Z"
}
```

### Webhook Handling

The system automatically handles Payme webhooks to update payment status and activate tariffs.

**Webhook URL:** `https://api.wedy.uz/payme/webhook`

**Security:** Webhooks are verified using HMAC-SHA256 signature validation.

**Supported Events:**
- `receipts.pay` - Payment successful
- `receipts.cancel` - Payment cancelled

### Database Schema

#### Payment Table

```sql
CREATE TABLE payment (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    amount INTEGER NOT NULL,
    status VARCHAR DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP NULL,
    payme_transaction_id VARCHAR NULL,
    payme_cheque_id VARCHAR NULL,
    tariff_id INTEGER NULL,
    payment_method VARCHAR DEFAULT 'PAYME',
    payme_error_code VARCHAR NULL,
    payme_error_message VARCHAR NULL,
    updated_at TIMESTAMP NULL,
    webhook_received_at TIMESTAMP NULL
);
```

#### User Table (Updated)

```sql
ALTER TABLE user ADD COLUMN tariff_id INTEGER NULL;
ALTER TABLE user ADD COLUMN tariff_expires_at TIMESTAMP NULL;
```

### Error Handling

The system provides comprehensive error handling:

- **Validation Errors**: Input validation with clear error messages
- **API Errors**: Payme API error handling with specific error codes
- **Webhook Errors**: Secure webhook processing with signature verification
- **Database Errors**: Transaction rollback on payment failures

### Testing

#### Test Mode Configuration

Set `PAYME_TEST_MODE=true` in your environment to use Payme's sandbox environment.

#### Test Payment Flow

1. Create a test tariff
2. Purchase the tariff using the API
3. Complete payment using test card details
4. Verify webhook processing and tariff activation

#### Test Cards (Sandbox)

Use Payme's test card details for sandbox testing:
- Card Number: `8600 1234 5678 9012`
- Expiry: Any future date
- CVV: Any 3 digits

### Security Considerations

1. **Webhook Security**: All webhooks are verified using HMAC signatures
2. **Input Validation**: All inputs are validated before processing
3. **Error Handling**: No sensitive data is exposed in error messages
4. **Admin Protection**: Sensitive endpoints require admin authentication
5. **Logging**: Comprehensive logging without sensitive data exposure

### Monitoring

Monitor the following for payment processing:

1. **Payment Status**: Track payment success/failure rates
2. **Webhook Processing**: Monitor webhook delivery and processing
3. **Tariff Activation**: Verify automatic tariff activation
4. **Error Rates**: Monitor API errors and webhook failures

### Troubleshooting

#### Common Issues

1. **Webhook Not Received**
   - Verify webhook URL in Payme dashboard
   - Check server accessibility
   - Verify signature validation

2. **Payment Creation Failed**
   - Check Payme credentials
   - Verify tariff exists and is active
   - Check amount validation

3. **Tariff Not Activated**
   - Verify webhook processing
   - Check payment status in Payme
   - Review error logs

#### Log Analysis

Check application logs for:
- Payment creation attempts
- Webhook processing
- Error messages
- Tariff activation

### Production Deployment

1. **Environment Variables**
   - Set `PAYME_TEST_MODE=false`
   - Use production Payme credentials
   - Configure production webhook URL

2. **SSL Certificate**
   - Ensure HTTPS for webhook endpoint
   - Valid SSL certificate required

3. **Monitoring**
   - Set up payment monitoring
   - Configure error alerts
   - Monitor webhook delivery

## Installation & Setup

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (optional, for caching)
- AWS S3 bucket (for file storage)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn app.main:app --reload
   ```

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/wedy_db

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# SMS (Eskiz)
ESKIZ_EMAIL=your-eskiz-email@example.com
ESKIZ_PASSWORD=your-eskiz-password

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=your-s3-bucket-name

# Payme Payment Gateway
PAYME_MERCHANT_ID=your-payme-merchant-id
PAYME_SECRET_KEY=your-payme-secret-key
PAYME_TEST_MODE=true
PAYME_CALLBACK_URL=https://api.wedy.uz/payme/webhook
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
