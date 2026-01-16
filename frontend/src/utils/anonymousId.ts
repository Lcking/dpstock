/**
 * Anonymous ID Management
 * Manages anonymous user identity for judgment tracking
 * Used before email binding
 */

const ANONYMOUS_ID_KEY = 'aguai_anonymous_id';

/**
 * Get or create anonymous ID
 * Called on app initialization
 * @returns anonymous_id (UUID)
 */
export function getOrCreateAnonymousId(): string {
    let id = localStorage.getItem(ANONYMOUS_ID_KEY);

    if (!id) {
        // Generate new UUID
        id = crypto.randomUUID();
        localStorage.setItem(ANONYMOUS_ID_KEY, id);
        console.log('[AnonymousId] Created new anonymous ID:', id);
    }

    return id;
}

/**
 * Get existing anonymous ID (without creating)
 * @returns anonymous_id or null
 */
export function getAnonymousId(): string | null {
    return localStorage.getItem(ANONYMOUS_ID_KEY);
}

/**
 * Clear anonymous ID (for testing)
 * WARNING: This will cause loss of anonymous judgments
 */
export function clearAnonymousId(): void {
    localStorage.removeItem(ANONYMOUS_ID_KEY);
    console.log('[AnonymousId] Cleared anonymous ID');
}
