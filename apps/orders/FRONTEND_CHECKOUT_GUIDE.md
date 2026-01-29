# Frontend Checkout Integration Guide

Quick guide to integrate the new checkout backend with your Next.js frontend.

## Overview

The new checkout endpoint handles everything server-side:
- ✅ Address creation/selection
- ✅ Order creation
- ✅ Coupon validation
- ✅ Amount calculation
- ✅ Guest and authenticated users

## API Endpoint

```
POST /api/orders/checkout/
```

## Request Payload

### For Logged-In Users (Existing Address)

```typescript
{
  address_id: 123,  // ID of saved address
  coupon_code: "SAVE10",  // optional
  payment_method: "COD",
  notes: "Please call before delivery"  // optional
}
```

### For Logged-In Users (New Address) or Guest Users

```typescript
{
  address: {
    name: "John Doe",
    phone: "01712345678",
    full_address: "123 Main St, Apt 4B",
    country: "BD",
    district: "Dhaka",
    postal_code: "1000",  // optional
    email: "john@example.com",  // optional
    is_default: false  // optional
  },
  coupon_code: "SAVE10",  // optional
  payment_method: "COD",
  notes: "Please call before delivery"  // optional
}
```

## Update CheckOut.tsx

### Step 1: Create Checkout Function

```typescript
// In CheckOut.tsx

const handleCheckout = async () => {
  try {
    // Prepare request payload
    const payload: any = {
      payment_method: "COD",
      notes: "",  // Add notes input if needed
    };
    
    // Case 1: User selected existing address
    if (selectedAddress && selectedAddress.id && !userExplicitlyChoseNew.current) {
      payload.address_id = parseInt(selectedAddress.id);
    }
    // Case 2: User entered new address or is guest
    else if (formData.name && formData.phone && formData.full_address) {
      payload.address = {
        name: formData.name.trim(),
        phone: formData.phone.trim(),
        full_address: formData.full_address.trim(),
        country: formData.country,
        district: formData.district.trim(),
        postal_code: formData.postal_code?.trim() || "",
        email: formData.email?.trim() || "",
        is_default: formData.is_default || false
      };
    }
    else {
      showErrorToast("Please provide a valid address.");
      return;
    }
    
    // Add coupon if applied
    if (appliedCoupon && appliedCoupon.code) {
      payload.coupon_code = appliedCoupon.code;
    }
    
    // Make API call
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
      
      // Clear cart (backend already marked it as ordered)
      dispatch(clearCart());
      
      // Redirect to orders page or thank you page
      router.push(`/orders/${result.order.id}`);
    } else {
      showErrorToast(result.error || "Failed to place order");
    }
  } catch (error: any) {
    console.error("Checkout error:", error);
    showErrorToast("An error occurred during checkout");
  }
};
```

### Step 2: Simplify Current Logic

Your current `handleCheckout` function (lines 577-690) can be replaced with the above. The backend now handles:
- Address creation
- Order creation  
- Cart clearing
- Coupon validation

**Remove these lines:**
```typescript
// REMOVE: Lines 584-654 (address creation logic)
// REMOVE: Lines 660-687 (order creation logic)

// The backend handles all of this now
```

**Keep these:**
```typescript
// KEEP: Validation logic (lines 555-575)
const isCheckoutDisabled = () => { ... }

// KEEP: Form state management
const [formData, setFormData] = useState({ ... })
```

### Step 3: Update Types

```typescript
// Add to your interfaces
interface CheckoutResponse {
  success: boolean;
  message?: string;
  order?: {
    id: number;
    order_number: string;
    total_amount: string;
    payable_amount: string;
    status: string;
    // ... other order fields
  };
  error?: string;
}
```

## Complete Example

### For Logged-In User with Existing Address

```typescript
const checkoutWithExistingAddress = async (addressId: string) => {
  const response = await fetch(`${API_URL}/orders/checkout/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      address_id: parseInt(addressId),
      coupon_code: appliedCoupon?.code,
      payment_method: 'COD'
    })
  });
  
  return await response.json();
};
```

### For Guest User

```typescript
const guestCheckout = async (address: AddressFormData) => {
  const response = await fetch(`${API_URL}/orders/checkout/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      address: {
        name: address.name,
        phone: address.phone,
        full_address: address.full_address,
        country: address.country,
        district: address.district,
        postal_code: address.postal_code || '',
        email: address.email || ''
      },
      payment_method: 'COD'
    })
  });
  
  return await response.json();
};
```

## Error Handling

```typescript
try {
  const result = await fetch(/* ... */);
  const data = await result.json();
  
  if (!result.ok) {
    // Handle HTTP errors
    if (result.status === 400) {
      showErrorToast(data.error || "Invalid request");
    } else if (result.status === 403) {
      showErrorToast("Permission denied");
    } else {
      showErrorToast("An error occurred");
    }
    return;
  }
  
  if (data.success) {
    // Success!
    showSuccessToast(data.message);
    router.push(`/orders/${data.order.id}`);
  } else {
    showErrorToast(data.error);
  }
} catch (error) {
  console.error("Checkout error:", error);
  showErrorToast("Network error occurred");
}
```

## Migration Checklist

### Remove from CheckOut.tsx
- [ ] Lines 433-471: Guest address localStorage logic
- [ ] Lines 584-654: Manual address creation in checkout
- [ ] Lines 660-687: Manual order creation logic
- [ ] Lines 490-495: localStorage address loading

### Keep in CheckOut.tsx
- [x] Form state (`formData`, `selectedAddress`)
- [x] Validation logic (`isCheckoutDisabled`)
- [x] Address selection UI
- [x] Coupon discount display
- [x] Cart items display

### Update in CheckOut.tsx
- [ ] `handleCheckout` function - replace with API call
- [ ] Remove `localStorage` for addresses (use backend API)
- [ ] Remove manual order creation
- [ ] Add proper error handling for API responses

## Benefits

### Before (Current)
```typescript
// Create address manually
const guestAddress = { id: Date.now(), ...addressData };
localStorage.setItem("shippingAddresses", JSON.stringify(updatedAddresses));

// Create order manually  
const newOrder = {
  orderId: randomId,
  totalPrice: total,
  products: cartItems,
  address: addressToUse,
  // ... manual calculations
};
dispatch(addOrder(newOrder));
```

### After (New Backend)
```typescript
// Single API call - backend handles everything
const response = await fetch('/api/orders/checkout/', {
  method: 'POST',
  body: JSON.stringify({
    address: addressData,
    coupon_code: couponCode
  })
});
```

✅ **Cleaner Code**: One API call instead of multiple steps  
✅ **Server-Side Validation**: Backend validates everything  
✅ **No localStorage**: Addresses saved to database  
✅ **Atomic Operations**: Everything in one transaction  
✅ **Better Error Handling**: Structured error responses  

## Testing

### Test Cases
1. **Logged-in user, existing address**
   - Select saved address
   - Click "Place Order"
   - Verify order created successfully

2. **Logged-in user, new address**
   - Enter new address
   - Click "Place Order"
   - Verify address saved and order created

3. **Guest user**
   - Enter address
   - Click "Place Order"
   - Verify order created with `is_guest=true`

4. **With coupon**
   - Apply coupon code
   - Place order
   - Verify discount applied correctly

5. **Error cases**
   - Empty cart → Should show error
   - Invalid coupon → Should show error
   - Missing address fields → Should show error

## Summary

The new backend checkout is:
- **Simpler**: One API call instead of multiple steps
- **Safer**: Server-side validation and calculations
- **Cleaner**: No localStorage management needed
- **Robust**: Atomic transactions with proper error handling

Replace your current multi-step checkout logic with a single API call to `/api/orders/checkout/` and let the backend handle the rest!
