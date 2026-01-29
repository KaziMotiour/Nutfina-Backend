# Checkout Backend Implementation

Clean, production-ready checkout flow for Django REST Framework supporting both authenticated and guest users.

## Architecture Overview

```
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │ POST /api/orders/checkout/
       ▼
┌────────────────────────────────┐
│  CheckoutView (API Layer)      │
│  - Validates request           │
│  - Handles errors              │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│  Checkout Service (Business)   │
│  - resolve_shipping_address()  │
│  - validate_cart()             │
│  - apply_coupon_discount()     │
│  - create_order_from_cart()    │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│  Database (Models)             │
│  - Address                     │
│  - Order                       │
│  - OrderItem                   │
└────────────────────────────────┘
```

## Files Structure

```
apps/orders/
├── checkout_serializers.py   # Request validation
├── checkout_service.py        # Business logic
├── checkout_views.py          # API endpoint
└── urls.py                    # URL routing
```

## API Contract

### Endpoint
```
POST /api/orders/checkout/
Content-Type: application/json
```

### Request Format

**Option 1: Logged-in user with existing address**
```json
{
  "address_id": 123,
  "coupon_code": "SAVE10",
  "payment_method": "COD",
  "notes": "Please call before delivery"
}
```

**Option 2: Logged-in user with new address OR guest user**
```json
{
  "address": {
    "name": "John Doe",
    "phone": "01712345678",
    "full_address": "123 Main St, Apt 4B",
    "country": "BD",
    "district": "Dhaka",
    "postal_code": "1000",
    "email": "john@example.com"
  },
  "coupon_code": "SAVE10",
  "payment_method": "COD",
  "notes": "Please call before delivery"
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address_id` | integer | Conditional* | ID of existing address (logged-in users only) |
| `address` | object | Conditional* | New address data |
| `address.name` | string | Yes (if address) | Full name |
| `address.phone` | string | Yes (if address) | Phone number |
| `address.full_address` | string | Yes (if address) | Complete address |
| `address.country` | string | Yes (if address) | ISO2 country code (e.g., "BD") |
| `address.district` | string | Yes (if address) | District/State |
| `address.postal_code` | string | No | Postal/ZIP code |
| `address.email` | string | No | Email address |
| `address.is_default` | boolean | No | Set as default address |
| `coupon_code` | string | No | Discount coupon code |
| `payment_method` | string | No | Payment method (default: "COD") |
| `notes` | string | No | Order notes/instructions |

\* Either `address_id` OR `address` must be provided, but not both.

### Success Response (201 Created)

```json
{
  "success": true,
  "message": "Order placed successfully",
  "order": {
    "id": 456,
    "order_number": "ORD-2026-001",
    "user": 123,
    "is_guest": false,
    "shipping_address": {
      "id": 789,
      "name": "John Doe",
      "phone": "01712345678",
      "full_address": "123 Main St, Apt 4B",
      "country": "BD",
      "district": "Dhaka",
      "postal_code": "1000"
    },
    "items": [
      {
        "id": 1,
        "product_name": "Product A",
        "variant_name": "Size M",
        "quantity": 2,
        "unit_price": "100.00",
        "line_total": "200.00"
      }
    ],
    "total_amount": "200.00",
    "discount_amount": "20.00",
    "payable_amount": "180.00",
    "coupon": {
      "code": "SAVE10",
      "description": "10% off"
    },
    "payment_method": "COD",
    "status": "pending",
    "created": "2026-01-24T10:30:00Z"
  }
}
```

### Error Response (400 Bad Request)

```json
{
  "success": false,
  "error": "Cart is empty."
}
```

### Error Response (403 Forbidden)

```json
{
  "success": false,
  "error": "You cannot use someone else's address."
}
```

## Business Logic Flow

### 1. Address Resolution

```python
# Step 1: Determine address source
if address_id:
    # Logged-in user selecting existing address
    - Verify user is authenticated
    - Fetch address from database
    - Verify address belongs to user
    - Return address
else if address_data:
    # New address (logged-in or guest)
    - Validate required fields
    - Create new Address
    - Set user=request.user if authenticated, else user=None
    - Return address
else:
    # Error: No address provided
    raise CheckoutError
```

### 2. Cart Validation

```python
# Step 2: Validate cart
- Get active cart (from get_active_cart service)
- Check cart exists
- Check cart has items
- For each item:
    - Verify product is still active
    - Verify sufficient inventory
```

### 3. Coupon Application

```python
# Step 3: Apply discount (if coupon provided)
if coupon_code:
    - Fetch coupon from database
    - Verify coupon is active
    - Check user eligibility
    - Calculate discount amount
    - Return (discount_amount, coupon)
else:
    - Return (0.00, None)
```

### 4. Order Creation

```python
# Step 4: Create order (atomic transaction)
- Calculate amounts:
    subtotal = cart.subtotal
    discount = coupon discount
    payable = subtotal - discount (minimum 0)
- Create Order:
    user = request.user if authenticated else None
    shipping_address = resolved address
    is_guest = not authenticated
    status = "pending"
- Create OrderItems from CartItems
- Mark cart as "ordered"
- Return order
```

## Validations

### Server-Side Validations

1. **Request Validation**
   - Either `address_id` or `address` must be provided
   - Cannot provide both `address_id` and `address`
   - All required address fields must be present

2. **Authentication Checks**
   - Guest users cannot use `address_id` (saved addresses)
   - Users can only use their own addresses

3. **Cart Validation**
   - Cart must exist
   - Cart must have items
   - All products must be active
   - Sufficient inventory for all items

4. **Coupon Validation**
   - Coupon must exist and be active
   - User must be eligible to use coupon
   - Cart subtotal must meet minimum requirements

5. **Amount Calculation**
   - All amounts calculated server-side
   - Frontend values are NOT trusted
   - Payable amount cannot be negative

### Security Measures

1. **Ownership Verification**
   ```python
   if address.user != request.user:
       raise PermissionDenied
   ```

2. **Atomic Transactions**
   ```python
   @transaction.atomic
   def create_order_from_cart(...):
       # All database operations are rolled back on error
   ```

3. **No Session Storage**
   - Everything persists in database
   - Guest orders use `user=None`, not sessions

## Error Handling

### Custom Exceptions

- **CheckoutError**: Business logic errors (400)
- **PermissionDenied**: Authorization errors (403)
- **Exception**: Unexpected errors (500)

### Error Messages

All errors return structured JSON:
```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

## Database Schema

### Order Model Fields
```python
user = ForeignKey(User, null=True)  # None for guest orders
shipping_address = ForeignKey(Address, on_delete=PROTECT)
coupon = ForeignKey(Coupon, null=True, blank=True)
total_amount = DecimalField()
discount_amount = DecimalField()
payable_amount = DecimalField()
payment_method = CharField(max_length=20)
notes = TextField(blank=True)
is_guest = BooleanField(default=False)
status = CharField(choices=STATUS_CHOICES)
```

### Address Model Fields
```python
user = ForeignKey(User, null=True)  # None for guest addresses
name = CharField(max_length=120)
phone = CharField(max_length=32)
full_address = CharField(max_length=500)
country = CountryField()
district = CharField(max_length=120)
postal_code = CharField(max_length=20, blank=True)
email = EmailField(blank=True)
is_default = BooleanField(default=False)
```

## Frontend Integration

### TypeScript Interface

```typescript
interface CheckoutRequest {
  address_id?: number;
  address?: {
    name: string;
    phone: string;
    full_address: string;
    country: string;
    district: string;
    postal_code?: string;
    email?: string;
    is_default?: boolean;
  };
  coupon_code?: string;
  payment_method?: string;
  notes?: string;
}
```

### Example: Logged-in user with existing address

```typescript
const checkoutWithExistingAddress = async (addressId: number) => {
  const response = await fetch('/api/orders/checkout/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      address_id: addressId,
      coupon_code: 'SAVE10',
      payment_method: 'COD',
      notes: 'Please call before delivery'
    })
  });
  
  return await response.json();
};
```

### Example: Guest user checkout

```typescript
const guestCheckout = async (addressData: AddressData) => {
  const response = await fetch('/api/orders/checkout/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      address: {
        name: addressData.name,
        phone: addressData.phone,
        full_address: addressData.full_address,
        country: addressData.country,
        district: addressData.district,
        postal_code: addressData.postal_code || '',
        email: addressData.email || ''
      },
      payment_method: 'COD'
    })
  });
  
  return await response.json();
};
```

## Testing Checklist

### Authenticated User Tests
- [ ] Checkout with existing address
- [ ] Checkout with new address
- [ ] Apply valid coupon code
- [ ] Apply invalid coupon code
- [ ] Try to use another user's address (should fail)
- [ ] Checkout with empty cart (should fail)

### Guest User Tests
- [ ] Checkout with new address
- [ ] Try to use address_id (should fail)
- [ ] Checkout without address (should fail)
- [ ] Verify order.is_guest = True
- [ ] Verify address.user = None

### Edge Cases
- [ ] Product becomes inactive after adding to cart
- [ ] Insufficient inventory
- [ ] Negative discount amount
- [ ] Both address_id and address provided (should fail)
- [ ] Missing required address fields
- [ ] Concurrent checkout requests

## Production Considerations

### 1. Inventory Management
Currently commented out - implement when ready:
```python
# reserve_stock_for_order(order, order.items.all())
```

### 2. Coupon Usage Tracking
Currently commented out - implement when ready:
```python
# CouponUsage.objects.create(...)
```

### 3. Logging
Add proper logging for production:
```python
import logging
logger = logging.getLogger(__name__)

try:
    order = process_checkout(...)
except Exception as e:
    logger.error(f"Checkout failed: {str(e)}", exc_info=True)
```

### 4. Email Notifications
Add email confirmation after successful checkout.

### 5. Payment Gateway Integration
Currently only supports COD. Add payment gateway integration when needed.

## Maintenance

### Adding New Payment Methods
Update the `payment_method` field choices in the Order model:
```python
PAYMENT_CHOICES = [
    ('COD', 'Cash on Delivery'),
    ('CARD', 'Credit/Debit Card'),
    ('BKASH', 'bKash'),
    # Add new methods here
]
```

### Adding New Order Statuses
Update the `STATUS_CHOICES` in the Order model.

## Summary

✅ **Clean Architecture**: Separated concerns (serializers, service, views)  
✅ **Type Safety**: Full validation with DRF serializers  
✅ **Security**: Ownership checks, atomic transactions  
✅ **Guest Support**: No authentication required  
✅ **Server-Side Calculations**: Frontend values not trusted  
✅ **Error Handling**: Structured, user-friendly errors  
✅ **Production Ready**: Follows Django/DRF best practices  

This implementation provides a robust, maintainable checkout flow without unnecessary complexity.
