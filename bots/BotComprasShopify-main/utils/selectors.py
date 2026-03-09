class Selectors:
    # Password page
    PASSWORD_INPUT = "input[type='password']"
    PASSWORD_SUBMIT = "button[type='submit']"

    # Storefront
    PRODUCT_LINKS = "a[href*='/products/']"
    COLLECTION_ALL = "/collections/all"

    # Product page
    ADD_TO_CART_BTN = "button[name='add']"
    QUANTITY_INPUT = "input[name='quantity']"
    VARIANT_SELECT = "select[name*='option'], .product-form__input select"

    # Cart drawer - checkout button inside the drawer that opens after add-to-cart
    CART_DRAWER_CHECKOUT = "cart-drawer button[name='checkout']"

    # Cart page fallback
    CART_PAGE_CHECKOUT = "button[name='checkout']"

    # Checkout - Contact
    EMAIL_INPUT = "input#email, input[type='email'], input[autocomplete='email'], input[name='email']"

    # Checkout - Shipping address (use id/name selectors matching the actual store)
    FIRST_NAME = "input[autocomplete='shipping given-name']:not([id^='autofill'])"
    LAST_NAME = "input[autocomplete='shipping family-name']:not([id^='autofill'])"
    ADDRESS1 = "input#shipping-address1"
    ADDRESS2 = "input[autocomplete='shipping address-line2']:not([id^='autofill'])"
    CITY = "input[autocomplete='shipping address-level2']:not([id^='autofill'])"
    PROVINCE = "select[name='zone']"
    ZIP_CODE = "input[autocomplete='shipping postal-code']:not([id^='autofill'])"
    COUNTRY = "select[name='countryCode']"

    # Checkout - Shipping method
    SHIPPING_METHOD_RADIO = "input[type='radio'][name*='shipping']"
    SHIPPING_METHODS_FIELDSET = "fieldset#shipping_methods"

    # Checkout - Payment iframes (ids are dynamic, match by partial id)
    CARD_NUMBER_IFRAME = "iframe[id^='card-fields-number']"
    CARD_NAME_IFRAME = "iframe[id^='card-fields-name']"
    CARD_EXPIRY_IFRAME = "iframe[id^='card-fields-expiry']"
    CARD_CVV_IFRAME = "iframe[id^='card-fields-verification']"

    # Checkout - Submit
    PAY_NOW_BTN = "button#checkout-pay-button"

    # Order confirmation
    ORDER_NUMBER = ".os-order-number, [data-order-number]"
