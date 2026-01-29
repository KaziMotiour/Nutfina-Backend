# Checkout Quick Start Guide

## 🚀 Quick Start

The checkout backend is **ready to use**. Here's how to integrate it:

## Backend (Already Done ✅)

```
POST /api/orders/checkout/
```

The endpoint handles:
- ✅ Address creation/selection
- ✅ Cart validation
- ✅ Coupon application
- ✅ Order creation
- ✅ Guest and authenticated users

## Frontend (3 Simple Steps)

### Step 1: Prepare Request Data

```typescript
// For logged-in user with existing address
const payload = {
  address_id: selectedAddress.id,
  coupon_code: appliedCoupon?.code,
  payment_method: "COD"
};

// OR for guest/new address
const payload = {
  address: {
    name: formData.name,
    phone: formData.phone,
    full_address: formData.full_address,
    country: formData.country,
    district: formData.district,
    postal_code: formData.postal_code || "",
    email: formData.email || ""
  },
  coupon_code: appliedCoupon?.code,
  payment_method: "COD"
};
```

### Step 2: Make API Call

```typescript
const response = await fetch(`${API_URL}/orders/checkout/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    ...(isLogin && { 'Authorization': `Bearer ${token}` })
  },
  body: JSON.stringify(payload)
});

const result = await response.json();
```

### Step 3: Handle Response

```typescript
if (result.success) {
  showSuccessToast("Order placed!");
  router.push(`/orders/${result.order.id}`);
} else {
  showErrorToast(result.error);
}
```

## That's It! 🎉

Replace your current `handleCheckout` function in `CheckOut.tsx` with the above 3 steps.

## Full Example

```typescript
const handleCheckout = async () => {
  // Validate
  if (!selectedAddress && !formData.name) {
    showErrorToast("Please provide an address");
    return;
  }
  
  // Prepare payload
  const payload: any = {
    payment_method: "COD",
  };
  
  if (selectedAddress?.id && !userExplicitlyChoseNew.current) {
    payload.address_id = parseInt(selectedAddress.id);
  } else {
    payload.address = {
      name: formData.name.trim(),
      phone: formData.phone.trim(),
      full_address: formData.full_address.trim(),
      country: formData.country,
      district: formData.district.trim(),
      postal_code: formData.postal_code?.trim() || "",
      email: formData.email?.trim() || ""
    };
  }
  
  if (appliedCoupon?.code) {
    payload.coupon_code = appliedCoupon.code;
  }
  
  // Make API call
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/orders/checkout/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(isLogin && { 'Authorization': `Bearer ${accessToken}` })
      },
      body: JSON.stringify(payload)
    });
    
    const result = await response.json();
    
    if (result.success) {
      showSuccessToast("Order placed successfully!");
      dispatch(clearCart());
      router.push(`/orders/${result.order.id}`);
    } else {
      showErrorToast(result.error || "Failed to place order");
    }
  } catch (error) {
    console.error("Checkout error:", error);
    showErrorToast("An error occurred during checkout");
  }
};
```

## What to Remove from CheckOut.tsx

Delete these sections (backend handles them now):

```typescript
// DELETE: Lines 433-471 (Guest address localStorage)
// DELETE: Lines 584-654 (Manual address creation)
// DELETE: Lines 660-687 (Manual order creation)
```

## API Response Structure

### Success (201)
```json
{
  "success": true,
  "message": "Order placed successfully",
  "order": {
    "id": 456,
    "order_number": "ORD-2026-001",
    "total_amount": "200.00",
    "discount_amount": "20.00",
    "payable_amount": "180.00",
    "status": "pending",
    ...
  }
}
```

### Error (400/403)
```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

## Testing

### Test 1: Logged-in user, existing address
```bash
curl -X POST http://localhost:8000/api/orders/checkout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"address_id": 1, "payment_method": "COD"}'
```

### Test 2: Guest user, new address
```bash
curl -X POST http://localhost:8000/api/orders/checkout/ \
  -H "Content-Type: application/json" \
  -d '{
    "address": {
      "name": "John Doe",
      "phone": "01712345678",
      "full_address": "123 Main St",
      "country": "BD",
      "district": "Dhaka"
    },
    "payment_method": "COD"
  }'
```

## Need More Info?

- **Full API docs**: `CHECKOUT_README.md`
- **Frontend guide**: `FRONTEND_CHECKOUT_GUIDE.md`
- **Implementation details**: `CHECKOUT_IMPLEMENTATION_SUMMARY.md`

## Summary

✅ **Backend ready** - Just call the API  
✅ **Clean & simple** - One endpoint, one call  
✅ **Fully documented** - Everything you need to know  
✅ **Production ready** - Secure, validated, atomic  

Replace your multi-step checkout with **3 simple steps** above! 🚀
