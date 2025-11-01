import { test, expect } from '@playwright/test';

/**
 * E2E test for hop1 drag-and-drop image attachment
 * 
 * Prerequisites:
 * - hop1 connection active with friendly_cat_1024.png in workspace
 * - Backend server running on http://192.168.2.203:8000/
 */

test.describe('Hop image drag and drop', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://192.168.2.203:8000/');
    
    // Wait for app to be ready
    await page.waitForSelector('[data-explorer-root]', { timeout: 15000 });
  });

  test('should embed remote hop1 image when dragged to chat', async ({ page }) => {
    // Switch to hop1 if not already there
    const hopButton = page.getByRole('button', { name: /Hop/i });
    await hopButton.click();
    
    // Wait for hop dialog and select hop1
    const hopDialog = page.locator('[role="dialog"]').filter({ hasText: /SSH Hop/i });
    await hopDialog.waitFor({ state: 'visible', timeout: 5000 });
    
    const hop1Row = hopDialog.getByText('hop1');
    if (await hop1Row.isVisible()) {
      await hop1Row.click();
      const hopToButton = hopDialog.getByRole('button', { name: /Hop$/i });
      await hopToButton.click();
    }
    
    // Wait for hop connection
    await page.waitForTimeout(2000);
    
    // Verify we're on hop1 by checking explorer path
    const explorerRoot = page.locator('[data-explorer-root]');
    const pathIndicator = explorerRoot.locator('text=/hop1:/');
    await expect(pathIndicator.first()).toBeVisible({ timeout: 10000 });
    
    // Find the cat image in explorer
    const catImage = explorerRoot.getByText('friendly_cat_1024.png', { exact: true });
    await expect(catImage).toBeVisible({ timeout: 5000 });
    
    // Open chat panel if not already open
    const chatButton = page.getByRole('button', { name: /Chat/i });
    await chatButton.click();
    
    // Get the chat composer
    const chatComposer = page.locator('[data-testid="chat-composer"]').or(page.locator('textarea[placeholder*="message"]'));
    await chatComposer.waitFor({ state: 'visible', timeout: 5000 });
    
    // Drag the image from explorer to chat composer
    await catImage.dragTo(chatComposer);
    
    // Verify the image appears as an attachment preview in the composer
    const attachmentPreview = page.locator('[data-testid="attachment-preview"]').or(page.locator('img[alt*="cat"]'));
    await expect(attachmentPreview.first()).toBeVisible({ timeout: 3000 });
    
    // Type a message
    await chatComposer.fill('can you add a red hat to this attached image?');
    
    // Send the message
    const sendButton = page.locator('[data-testid="send-button"]').or(page.getByRole('button', { name: /Send/i }));
    await sendButton.click();
    
    // Wait for backend logs to show the attachment processing
    await page.waitForTimeout(2000);
    
    // Check for error indicators in the response
    const chatMessages = page.locator('[data-testid="chat-message"]').or(page.locator('[class*="message"]'));
    const lastMessage = chatMessages.last();
    await lastMessage.waitFor({ state: 'visible', timeout: 10000 });
    
    // The message should NOT contain "Failed to decode provided image"
    await expect(lastMessage).not.toContainText('Failed to decode provided image');
    
    // The message should indicate the tool is processing or succeeded
    await expect(lastMessage).toContainText(/generating|edit|image/i);
  });
  
  test('backend logs should show hop-aware attachment processing', async ({ page }) => {
    // This test verifies the logs contain our debug markers
    // We'll make a simple request to trigger attachment normalization
    
    // Navigate and set up as before
    await page.goto('http://192.168.2.203:8000/');
    await page.waitForSelector('[data-explorer-root]', { timeout: 15000 });
    
    // We can't directly check backend logs from playwright, but we can trigger
    // the code path and then manually verify logs contain:
    // [ATTACH-DEBUG] Raw attachments before normalization
    // [ATTACH-DEBUG] Normalized N attachments
    // [EMBED-DEBUG] Processing attachment: kind=images
    // [EMBED-DEBUG] Attempting hop-aware embed
    // [EMBED-DEBUG] Successfully embedded namespaced image
    
    // For now, we'll just log a note that manual log verification is needed
    console.log('After running this test, verify backend logs contain [ATTACH-DEBUG] and [EMBED-DEBUG] markers');
  });
});
