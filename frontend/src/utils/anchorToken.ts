/**
 * Anchor (email binding) status management.
 *
 * After the unified-auth migration the anchor token is no longer stored
 * separately — it is the same token as the main `token` in localStorage.
 * We keep this module's public API unchanged so existing components
 * (AnchorStatus, AnchorBindDialog, etc.) continue to work without changes.
 *
 * "Is the user email-bound?" is now determined by whether a masked email
 * is stored in localStorage.
 */

const MASKED_EMAIL_KEY = 'aguai_masked_email';

/**
 * After a successful email-bind, store the unified token as the main token.
 * (The backend now returns a unified JWT from verify_and_bind.)
 */
export function saveAnchorToken(token: string): void {
    localStorage.setItem('token', token);
    console.log('[AnchorToken] Saved unified token after email binding');
}

/**
 * Check if the user has bound their email.
 */
export function hasAnchorToken(): boolean {
    return !!localStorage.getItem(MASKED_EMAIL_KEY);
}

/**
 * Get the current auth token (unified).
 */
export function getAnchorToken(): string | null {
    return localStorage.getItem('token');
}

/**
 * Clear binding state (logout / unbind).
 */
export function clearAnchorToken(): void {
    localStorage.removeItem(MASKED_EMAIL_KEY);
    console.log('[AnchorToken] Cleared email binding status');
}

// ---------------------------------------------------------------------------
// Masked email helpers
// ---------------------------------------------------------------------------

export function saveMaskedEmail(email: string): void {
    localStorage.setItem(MASKED_EMAIL_KEY, email);
}

export function getMaskedEmail(): string | null {
    return localStorage.getItem(MASKED_EMAIL_KEY);
}

export function clearMaskedEmail(): void {
    localStorage.removeItem(MASKED_EMAIL_KEY);
}
