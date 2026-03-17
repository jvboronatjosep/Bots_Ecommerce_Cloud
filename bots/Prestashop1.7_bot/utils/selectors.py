class Selectors:
    # ── Product listing ───────────────────────────────────────────────────────
    COLLECTION_PATH = "/index.php"
    PRODUCT_LINKS   = "a.product-thumbnail, a.thumbnail.product-thumbnail, .product-miniature a.thumbnail"

    # ── Product page ──────────────────────────────────────────────────────────
    VARIANT_SELECT  = "select.form-control"          # PS1.7 modern: <select> dropdown
    ADD_TO_CART_BTN = "button.add-to-cart"

    # ── Cart page ─────────────────────────────────────────────────────────────
    CART_PROCEED    = ".cart-detailed-actions a.btn, a[href*='controller=order'], a[href*='checkout']"

    # ── Checkout /index.php?controller=order ──────────────────────────────────
    # Step 1 — Guest personal info
    GUEST_GENDER_MR  = "input[name='id_gender'][value='1']"
    GUEST_GENDER_MRS = "input[name='id_gender'][value='2']"
    GUEST_FIRSTNAME  = "input[name='firstname']"
    GUEST_LASTNAME   = "input[name='lastname']"
    GUEST_EMAIL      = "input[name='email']"

    # Step 2 — Address
    ADDRESS_ADDRESS1 = "input[name='address1']"
    ADDRESS_POSTCODE = "input[name='postcode']"
    ADDRESS_CITY     = "input[name='city']"
    ADDRESS_PHONE    = "input[name='phone']"
    ADDRESS_ALIAS    = "input[name='alias']"

    # Step continue buttons (same IDs as PS8 modern theme)
    CHECKOUT_CONTINUE_PERSONAL = "button[name='continue'], button.continue[type='submit']"
    CHECKOUT_CONTINUE_ADDRESS  = "button[name='confirm-addresses'], button.continue[type='submit']"
    CHECKOUT_CONTINUE_DELIVERY = "button[name='confirmDeliveryOption']"

    # Step 4 — Payment
    PAYMENT_OPTION      = "input.payment-option"
    PAYMENT_TERMS       = "input[name='conditions_to_approve[terms-and-conditions]']"
    PAYMENT_PLACE_ORDER = "#payment-confirmation button[type='submit']"

    # ── Order confirmation ────────────────────────────────────────────────────
    ORDER_CONFIRM_URL   = "controller=order-confirmation"
