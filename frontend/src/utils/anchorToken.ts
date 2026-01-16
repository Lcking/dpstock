/**
 * Anchor Token Management
 * Manages anchor (email binding) token for cross-device access
 */

const ANCHOR_TOKEN_KEY = 'aguai_anchor_token';

/**
 * Save anchor token after successful binding
 * @param token - JWT token from backend
 */
export function saveAnchorToken(token: string): void {
    localStorage.setItem(ANCHOR_TOKEN_KEY, token);
    console.log('[AnchorToken] Saved anchor token');
}

/**
 * Get anchor token
 * @returns token or null
 */
export function getAnchorToken(): string | null {
    return localStorage.getItem(ANCHOR_TOKEN_KEY);
}

/**
 * Check if user has anchor token (is bound)
 * @returns true if bound
 */
export function hasAnchorToken(): boolean {
    return !!localStorage.getItem(ANCHOR_TOKEN_KEY);
}

/**
 * Clear anchor token (logout)
 */
export function clearAnchorToken(): void {
    localStorage.removeItem(ANCHOR_TOKEN_KEY);
    console.log('[AnchorToken] Cleared anchor token');
}

/**
 * Get masked email from localStorage
 * Saved during binding process
 */
const MASKED_EMAIL_KEY = 'aguai_masked_email';

export function saveMaskedEmail(email: string): void {
    localStorage.setItem(MASKED_EMAIL_KEY, email);
}

export function getMaskedEmail(): string | null {
    return localStorage.getItem(MASKED_EMAIL_KEY);
}

export function clearMaskedEmail(): void {
    localStorage.removeItem(MASKED_EMAIL_KEY);
}
