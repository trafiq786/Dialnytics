# Update H
1. Customer usage (Calls, Talk time, Estimated Provider Cost, Margin) now follows the plan cycle
   (renewal date - 30 days .. renewal date), not the calendar month. It resets on renewal.
2. CRM: checkboxes + "Select all" + "Delete selected" (bulk), single Delete works even for leads in a queue.
3. Power Dialer: lead picker has Delete per lead and Delete selected (bulk); queue updates automatically.
4. Customer details: Payment History has an Edit button (PKR, USD, method, reference) and Delete payment;
   customer's paid price (last_paid_amount) follows the newest payment.
5. Premium confirm popup shared on all pages (static/js/confirm-modal.js).
Copy files over the project, redeploy. No database migration needed.
