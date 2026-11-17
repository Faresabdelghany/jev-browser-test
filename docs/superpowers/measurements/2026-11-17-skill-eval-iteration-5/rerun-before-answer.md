**Nothing is different from yesterday.** I reran the suite the same way (8 specs, 1 run each, 2 at a time, headless; say *headed* to watch): 8 browser runs, 17.2 s, all green.

| spec | yesterday | today |
|---|---|---|
| `add-remove-elements` | pass (`one_delete_left`) | same |
| `forgot-password` | pass (`email_sent`) | same |
| `login-logout` | pass (`logged_out`) | same |
| `shop-add-second-item` | pass (`bike_light_in_cart`) | same |
| `shop-checkout` | pass (`order_complete`) | same |
| `shop-checkout-error-account` | expected red (`undetermined`, blocked, as the spec declares) | same |
| `todo-add-filter` | pass (`active_filtered`) | same |
| `web-form-submit` | pass (`form_submitted`) | same |

- **Same endings, same evidence:** each spec reached the same outcome and quoted the same line from the page (for example "Checkout: Complete!" and "Your e-mail's been sent!").
- **Same path:** each spec used the same number of Jev requests and the same input tokens as yesterday, so the pages looked the same to the runner.
- **Only noise moved:** run times differ by about 0.2 s at most, and decision confidence shifted by up to 0.04.

This is one run per spec, so it shows today matches yesterday, not how stable each spec is.

Today's results are in `runs/suite/today/results.md`.
