# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: integration.test.ts >> Integration Test for All Roles >> Test login and dashboard for operator
- Location: integration.test.ts:18:9

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.fill: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('input[type="email"]')

```

# Test source

```ts
  1  | import { test, expect, Page } from '@playwright/test';
  2  | 
  3  | const USERS = [
  4  |   { email: 'operator@edgetwin.ai', role: 'operator', dashboard: '/operator' },
  5  |   { email: 'manager@edgetwin.ai', role: 'maintenance_manager', dashboard: '/maintenance' },
  6  |   { email: 'technician@edgetwin.ai', role: 'mechanic', dashboard: '/mechanic' },
  7  |   { email: 'production@edgetwin.ai', role: 'production_manager', dashboard: '/production' },
  8  |   { email: 'owner@edgetwin.ai', role: 'factory_owner', dashboard: '/owner' },
  9  |   { email: 'admin@edgetwin.ai', role: 'admin', dashboard: '/admin' }
  10 | ];
  11 | 
  12 | const PASSWORD = 'EdgeTwin@2026';
  13 | const BASE_URL = 'http://localhost:5173';
  14 | 
  15 | test.describe('Integration Test for All Roles', () => {
  16 | 
  17 |   for (const user of USERS) {
  18 |     test(`Test login and dashboard for ${user.role}`, async ({ page }) => {
  19 |       let consoleErrors: string[] = [];
  20 |       let failedRequests: string[] = [];
  21 | 
  22 |       page.on('console', msg => {
  23 |         if (msg.type() === 'error') {
  24 |           consoleErrors.push(msg.text());
  25 |         }
  26 |       });
  27 | 
  28 |       page.on('requestfinished', request => {
  29 |         const response = request.response();
  30 |         if (response && typeof response.status === 'function' ? response.status() >= 400 : (response as any).status >= 400 && request.url().includes('localhost')) {
  31 |           failedRequests.push(`Failed Request: ${request.method()} ${request.url()} - ${typeof response.status === 'function' ? response.status() : (response as any).status}`);
  32 |         }
  33 |       });
  34 | 
  35 |       page.on('requestfailed', request => {
  36 |         if (request.url().includes('localhost')) {
  37 |             failedRequests.push(`Failed Request: ${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
  38 |         }
  39 |       });
  40 | 
  41 |       // 1. Login works
  42 |       await page.goto(`${BASE_URL}/login`);
> 43 |       await page.fill('input[type="email"]', user.email);
     |                  ^ Error: page.fill: Test timeout of 30000ms exceeded.
  44 |       await page.fill('input[type="password"]', PASSWORD);
  45 |       await page.click('button[type="submit"]');
  46 | 
  47 |       // 2. Redirects to correct dashboard
  48 |       await page.waitForURL(`**${user.dashboard}`, { timeout: 10000 });
  49 |       expect(page.url()).toContain(user.dashboard);
  50 | 
  51 |       // Wait a bit for the dashboard to settle and APIs to resolve
  52 |       await page.waitForTimeout(3000);
  53 | 
  54 |       // 3. No blank pages - check if body has children
  55 |       const content = await page.textContent('body');
  56 |       expect(content?.trim().length).toBeGreaterThan(0);
  57 | 
  58 |       // 4. No console errors
  59 |       // Note: We might see some expected errors, but ideally none.
  60 |       expect(consoleErrors).toEqual([]);
  61 | 
  62 |       // 5. No failed API requests
  63 |       expect(failedRequests).toEqual([]);
  64 | 
  65 |       // 6. Navigation links work (click first navigation link inside sidebar)
  66 |       // We will look for some nav links
  67 |       const navLinks = await page.locator('nav a');
  68 |       if (await navLinks.count() > 0) {
  69 |           const href = await navLinks.first().getAttribute('href');
  70 |           if (href) {
  71 |               await navLinks.first().click();
  72 |               await page.waitForTimeout(1000);
  73 |               expect(page.url()).toContain(href);
  74 |           }
  75 |       }
  76 | 
  77 |       // Logout if possible or just clear cookies for next test
  78 |       await page.context().clearCookies();
  79 |     });
  80 |   }
  81 | });
  82 | 
```