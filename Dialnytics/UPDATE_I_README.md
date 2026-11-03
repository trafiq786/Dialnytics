# Update I - new animated sign-in page
- Full-screen animated login (cursor spotlight, parallax, card tilt, wave bars, password show/hide).
- Marketing-site logo (dialnytics-logo-light.png) on the dark background.
- "New here? See it in action / Take the tour" card + header link -> https://dialnytics.uk/product/tour/
  (change with env var PRODUCT_TOUR_URL on Render).
- Login form, error message and CSRF unchanged (POST /login).
- backend/main.py includes Update H as well; this file replaces it.
