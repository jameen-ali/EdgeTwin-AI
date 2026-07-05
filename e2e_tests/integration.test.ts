import { test, expect, Page } from '@playwright/test';

const USERS = [
  { email: 'operator@edgetwin.ai', role: 'operator', dashboard: '/operator' },
  { email: 'manager@edgetwin.ai', role: 'maintenance_manager', dashboard: '/maintenance' },
  { email: 'technician@edgetwin.ai', role: 'mechanic', dashboard: '/mechanic' },
  { email: 'production@edgetwin.ai', role: 'production_manager', dashboard: '/production' },
  { email: 'owner@edgetwin.ai', role: 'factory_owner', dashboard: '/owner' },
  { email: 'admin@edgetwin.ai', role: 'admin', dashboard: '/admin' }
];

const PASSWORD = 'EdgeTwin@2026';
const BASE_URL = 'http://localhost:5173';

test.describe('Integration Test for All Roles', () => {

  for (const user of USERS) {
    test(`Test login and dashboard for ${user.role}`, async ({ page }) => {
      let consoleErrors: string[] = [];
      let failedRequests: string[] = [];

      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      page.on('requestfinished', request => {
        const response = request.response();
        if (response && typeof response.status === 'function' ? response.status() >= 400 : (response as any).status >= 400 && request.url().includes('localhost')) {
          failedRequests.push(`Failed Request: ${request.method()} ${request.url()} - ${typeof response.status === 'function' ? response.status() : (response as any).status}`);
        }
      });

      page.on('requestfailed', request => {
        if (request.url().includes('localhost')) {
            failedRequests.push(`Failed Request: ${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
        }
      });

      // 1. Login works
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', user.email);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button[type="submit"]');

      // 2. Redirects to correct dashboard
      await page.waitForURL(`**${user.dashboard}`, { timeout: 10000 });
      expect(page.url()).toContain(user.dashboard);

      // Wait a bit for the dashboard to settle and APIs to resolve
      await page.waitForTimeout(3000);

      // 3. No blank pages - check if body has children
      const content = await page.textContent('body');
      expect(content?.trim().length).toBeGreaterThan(0);

      // 4. No console errors
      // Note: We might see some expected errors, but ideally none.
      expect(consoleErrors).toEqual([]);

      // 5. No failed API requests
      expect(failedRequests).toEqual([]);

      // 6. Navigation links work (click first navigation link inside sidebar)
      // We will look for some nav links
      const navLinks = await page.locator('nav a');
      if (await navLinks.count() > 0) {
          const href = await navLinks.first().getAttribute('href');
          if (href) {
              await navLinks.first().click();
              await page.waitForTimeout(1000);
              expect(page.url()).toContain(href);
          }
      }

      // Logout if possible or just clear cookies for next test
      await page.context().clearCookies();
    });
  }
});
